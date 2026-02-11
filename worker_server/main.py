"""
FastAPI worker server for Campaign Builder.
Runs on Mac Mini Pros to execute create_campaigns_v2_sync.py jobs.
"""

import os
import socket
import subprocess
import threading
import uuid
from collections import deque
from pathlib import Path

from fastapi import FastAPI, HTTPException
from worker_server.models import CreateJobRequest, JobResponse, HealthResponse, AdCsvListResponse

app = FastAPI(title="Campaign Builder Worker")

# In-memory job store (sufficient for 1-2 concurrent jobs per MBP)
jobs: dict[str, dict] = {}
job_lock = threading.Lock()

# TJ_tool root directory (parent of worker_server/)
TJ_TOOL_DIR = Path(__file__).parent.parent
CAMPAIGN_CREATION_DIR = TJ_TOOL_DIR / "data" / "input" / "Campaign_Creation"
MULTILINGUAL_DIR = TJ_TOOL_DIR / "data" / "input" / "Multilingual_Campaign_Creation"
SCRIPT_PATH = TJ_TOOL_DIR / "create_campaigns_v2_sync.py"


def _get_ad_csvs() -> dict[str, list[str]]:
    """List available ad CSV files from both input directories."""
    result: dict[str, list[str]] = {}
    for label, directory in [("Campaign_Creation", CAMPAIGN_CREATION_DIR), ("Multilingual_Campaign_Creation", MULTILINGUAL_DIR)]:
        if directory.exists():
            result[label] = sorted([
                f.name for f in directory.iterdir()
                if f.is_file() and f.suffix.lower() == '.csv'
            ])
    return result


def _run_job(job_id: str, csv_path: str, dry_run: bool):
    """Run create_campaigns_v2_sync.py in a subprocess (background thread)."""
    cmd = [
        "python", str(SCRIPT_PATH),
        "--input", csv_path,
        "--headless",
    ]
    if dry_run:
        cmd.append("--dry-run")

    with job_lock:
        jobs[job_id]["status"] = "running"

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(TJ_TOOL_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, "WORKER_ID": "galactus"},
        )
        with job_lock:
            jobs[job_id]["process"] = proc

        log_lines: deque[str] = deque(maxlen=50)
        campaigns_created = 0

        for line in proc.stdout:  # type: ignore[union-attr]
            line = line.rstrip()
            log_lines.append(line)
            # Count campaigns by looking for success markers in output
            if "Campaign created successfully" in line or "✓" in line:
                campaigns_created += 1
            with job_lock:
                jobs[job_id]["log_lines"] = list(log_lines)
                jobs[job_id]["campaigns_created"] = campaigns_created

        proc.wait()

        with job_lock:
            if proc.returncode == 0:
                jobs[job_id]["status"] = "completed"
            else:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = f"Process exited with code {proc.returncode}"

    except Exception as e:
        with job_lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)


@app.get("/health", response_model=HealthResponse)
def health():
    hostname = socket.gethostname()
    with job_lock:
        active = sum(1 for j in jobs.values() if j["status"] in ("pending", "running"))
    return HealthResponse(
        hostname=hostname,
        active_jobs=active,
        available_ad_csvs=_get_ad_csvs(),
    )


@app.get("/ad-csvs", response_model=AdCsvListResponse)
def list_ad_csvs():
    return AdCsvListResponse(csv_files=_get_ad_csvs())

# Also keep a flat list endpoint for backward compat
@app.get("/ad-csvs/flat")
def list_ad_csvs_flat():
    all_csvs = _get_ad_csvs()
    flat = []
    for csvs in all_csvs.values():
        flat.extend(csvs)
    return {"csv_files": sorted(set(flat))}


@app.post("/jobs", response_model=JobResponse)
def create_job(req: CreateJobRequest):
    # Check max concurrent jobs (1 at a time)
    with job_lock:
        running = sum(1 for j in jobs.values() if j["status"] in ("pending", "running"))
        if running >= 1:
            raise HTTPException(
                status_code=429,
                detail="Worker is busy. Max 1 concurrent job allowed.",
            )

    job_id = str(uuid.uuid4())

    # Write CSV into Multilingual_Campaign_Creation dir so the script
    # resolves ad CSV paths (csv_file column) relative to this directory.
    # create_campaigns_v2_sync.py sets csv_dir = input_file.parent
    input_dir = TJ_TOOL_DIR / "data" / "input" / "Multilingual_Campaign_Creation"
    input_dir.mkdir(parents=True, exist_ok=True)
    csv_path = input_dir / "temp_batch_galactus.csv"
    csv_path.write_text(req.csv_content)

    # Count expected campaigns from CSV (lines minus header)
    lines = [l for l in req.csv_content.strip().split("\n") if l.strip()]
    total_campaigns = max(0, len(lines) - 1)  # subtract header

    with job_lock:
        jobs[job_id] = {
            "status": "pending",
            "csv_path": str(csv_path),
            "dry_run": req.dry_run,
            "campaigns_created": 0,
            "total_campaigns": total_campaigns,
            "log_lines": [],
            "error": None,
            "process": None,
        }

    # Launch in background thread
    thread = threading.Thread(target=_run_job, args=(job_id, str(csv_path), req.dry_run), daemon=True)
    thread.start()

    return JobResponse(
        job_id=job_id,
        status="pending",
        total_campaigns=total_campaigns,
    )


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    with job_lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(
        job_id=job_id,
        status=job["status"],
        campaigns_created=job["campaigns_created"],
        total_campaigns=job["total_campaigns"],
        log_lines=job["log_lines"],
        error=job.get("error"),
    )


@app.delete("/jobs/{job_id}")
def cancel_job(job_id: str):
    with job_lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    proc = job.get("process")
    if proc and proc.poll() is None:
        proc.terminate()
        with job_lock:
            jobs[job_id]["status"] = "cancelled"
        return {"message": "Job cancelled"}
    return {"message": "Job is not running"}
