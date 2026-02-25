"""
FastAPI worker server for Campaign Builder.
Runs on Mac Mini Pros to execute campaign creation jobs.

Supports CSV formats:
- Multilingual: has lang_code, ad_csv_straight columns → runs create_multilingual.py
- Standard: has group, csv_file, variants, enabled → runs create_campaigns_v2_sync.py
- V4: has ad_format_type column → runs create_campaigns_v4.py

Supports parallel browser workers (1-4) with screen quadrant positioning and session sharing.
"""
from __future__ import annotations

import csv
import io
import os
import re
import socket
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from pathlib import Path

from fastapi import FastAPI, HTTPException
from worker_server.models import CreateJobRequest, JobResponse, HealthResponse, AdCsvListResponse

app = FastAPI(title="Campaign Builder Worker")

# Mount campaign scraper sub-app at /scraper
try:
    from src.campaign_scraper.server import app as scraper_app
    app.mount("/scraper", scraper_app)
except ImportError as e:
    print(f"Warning: Campaign scraper not available: {e}")

# In-memory job store (sufficient for 1-2 concurrent jobs per MBP)
jobs: dict[str, dict] = {}
job_lock = threading.Lock()

# TJ_tool root directory (parent of worker_server/)
TJ_TOOL_DIR = Path(__file__).parent.parent
CAMPAIGN_CREATION_DIR = TJ_TOOL_DIR / "data" / "input" / "Campaign_Creation"
MULTILINGUAL_DIR = TJ_TOOL_DIR / "data" / "input" / "Multilingual_Campaign_Creation"
MULTILINGUAL_SCRIPT = TJ_TOOL_DIR / "create_multilingual.py"
STANDARD_SCRIPT = TJ_TOOL_DIR / "create_campaigns_v2_sync.py"
TEMPLATE_SCRIPT = TJ_TOOL_DIR / "create_templates.py"
TEMPLATE_DIR = TJ_TOOL_DIR / "data" / "input" / "Template_Creation"
V4_SCRIPT = TJ_TOOL_DIR / "create_campaigns_v4.py"
V4_DIR = TJ_TOOL_DIR / "data" / "output" / "V4_Campaign_Export"
SESSION_FILE = TJ_TOOL_DIR / "data" / "session" / "tj_session.json"
LOG_DIR = TJ_TOOL_DIR / "logs"

# Regex patterns for log parsing
ID_PATTERN = re.compile(r'(?:^|\s)ID:\s*(\d+)')
TOTAL_PATTERN = re.compile(r'Found\s+(\d+)\s+enabled\s+campaign')
VARIANT_TOTAL_PATTERN = re.compile(r'TOTAL:\s*\d+\s*campaign rows\s*->\s*(\d+)\s*campaign variants')
CAMPAIGN_CSV_PATTERN = re.compile(r'Campaign CSV:\s*(.+)')


def _get_ad_csvs() -> dict[str, list[str]]:
    """List available ad CSV files from both input directories."""
    result: dict[str, list[str]] = {}
    for label, directory in [("Campaign_Creation", CAMPAIGN_CREATION_DIR), ("Multilingual_Campaign_Creation", MULTILINGUAL_DIR), ("V4_Campaign_Export", V4_DIR)]:
        if directory.exists():
            result[label] = sorted([
                f.name for f in directory.iterdir()
                if f.is_file() and f.suffix.lower() == '.csv'
            ])
    return result


def _detect_csv_format(csv_content: str) -> str:
    """Detect whether CSV is multilingual or standard format."""
    reader = csv.reader(io.StringIO(csv_content))
    try:
        headers = [h.strip().lower() for h in next(reader)]
    except StopIteration:
        return "standard"

    if "ad_format_type" in headers:
        return "v4"
    if "lang_code" in headers:
        return "multilingual"
    return "standard"


def _extract_multilingual_params(csv_content: str) -> dict:
    """Extract --format and --group from the first data row of a multilingual CSV."""
    reader = csv.DictReader(io.StringIO(csv_content))
    for row in reader:
        row = {k.strip().lower(): v.strip() for k, v in row.items()}
        return {
            "ad_format": (row.get("ad_format") or "NATIVE").upper(),
            "group": row.get("group") or row.get("lang_name") or "i18n",
        }
    return {"ad_format": "NATIVE", "group": "i18n"}


def _build_command(csv_path: str, csv_content: str, dry_run: bool, flow: str | None = None) -> tuple[list[str], str, str]:
    """Build the command to run based on CSV format.

    Returns (command, flow_used, flow_source) where flow_source is 'explicit' or 'auto-detected'.
    """
    if flow in ("multilingual", "standard", "template", "v4"):
        fmt = flow
        flow_source = "explicit"
    else:
        fmt = _detect_csv_format(csv_content)
        flow_source = "auto-detected"

    if fmt == "multilingual":
        params = _extract_multilingual_params(csv_content)
        cmd = [
            sys.executable, str(MULTILINGUAL_SCRIPT),
            "--languages", csv_path,
            "--format", params["ad_format"],
            "--group", params["group"],
            "--live",
            "--create-campaigns",
            "--no-headless",
        ]
        if dry_run:
            # For dry run, skip --live and --create-campaigns
            cmd = [
                sys.executable, str(MULTILINGUAL_SCRIPT),
                "--languages", csv_path,
                "--format", params["ad_format"],
                "--group", params["group"],
            ]
    elif fmt == "v4":
        cmd = [sys.executable, str(V4_SCRIPT), csv_path, "--live"]
        if dry_run:
            cmd.append("--dry-run")
    elif fmt == "template":
        cmd = [
            sys.executable, str(TEMPLATE_SCRIPT),
            "--input", csv_path,
            "--live",
            "--no-headless",
        ]
        if dry_run:
            cmd = [
                sys.executable, str(TEMPLATE_SCRIPT),
                "--input", csv_path,
                "--dry-run",
            ]
    else:
        cmd = [
            sys.executable, str(STANDARD_SCRIPT),
            "--input", csv_path,
        ]
        if dry_run:
            cmd.append("--dry-run")

    return cmd, fmt, flow_source


# ============================================================================
# PARALLEL WORKER HELPERS
# ============================================================================

def _detect_screen_resolution() -> tuple[int, int]:
    """Auto-detect logical screen resolution on macOS.

    Uses 'UI Looks like' (logical/HiDPI resolution) which matches what Chromium
    uses for --window-position and --window-size. Falls back to native resolution
    divided by 2 if UI Looks like is not available.
    """
    try:
        result = subprocess.run(
            ['system_profiler', 'SPDisplaysDataType'],
            capture_output=True, text=True, timeout=5,
        )
        # Prefer "UI Looks like" (logical resolution for HiDPI/Retina displays)
        ui_match = re.search(r'UI Looks like:\s+(\d+)\s*x\s*(\d+)', result.stdout)
        if ui_match:
            return int(ui_match.group(1)), int(ui_match.group(2))
        # Fallback: native resolution (assume 2x scaling on Retina)
        native_match = re.search(r'Resolution:\s+(\d+)\s*x\s*(\d+)', result.stdout)
        if native_match:
            w, h = int(native_match.group(1)), int(native_match.group(2))
            # If resolution looks like 4K+, assume 2x Retina scaling
            if w >= 2560:
                return w // 2, h // 2
            return w, h
    except Exception:
        pass
    return 1920, 1080


def _compute_quadrants(num_workers: int) -> list[dict]:
    """Calculate window position/size for each worker. All workers run full screen."""
    sw, sh = _detect_screen_resolution()
    return [{"x": 0, "y": 0, "w": sw, "h": sh} for _ in range(num_workers)]


def _split_csv_content(csv_content: str, num_workers: int) -> list[str]:
    """Split CSV content into N chunks, preserving the header row."""
    lines = csv_content.strip().split('\n')
    if len(lines) <= 1:
        return [csv_content]
    header = lines[0]
    data_rows = [l for l in lines[1:] if l.strip()]
    if len(data_rows) == 0:
        return [csv_content]
    chunk_size = max(1, (len(data_rows) + num_workers - 1) // num_workers)
    chunks = []
    for i in range(0, len(data_rows), chunk_size):
        chunk = header + '\n' + '\n'.join(data_rows[i:i + chunk_size])
        chunks.append(chunk)
    return chunks


def _parse_log_file(log_path: Path) -> tuple[list[str], list[str], int]:
    """Parse a worker log file. Returns (campaign_ids, log_lines, total_found)."""
    campaign_ids: list[str] = []
    log_lines: list[str] = []
    total_found = 0
    try:
        if log_path.exists():
            text = log_path.read_text()
            for line in text.splitlines():
                log_lines.append(line)
                m = ID_PATTERN.search(line)
                if m:
                    campaign_ids.append(m.group(1))
                mt = TOTAL_PATTERN.search(line)
                if mt:
                    total_found = max(total_found, int(mt.group(1)))
                mv = VARIANT_TOTAL_PATTERN.search(line)
                if mv:
                    total_found = max(total_found, int(mv.group(1)))
    except Exception:
        pass
    return campaign_ids, log_lines, total_found


# ============================================================================
# SINGLE-PROCESS JOB (original behavior, used for workers=1 or dry_run)
# ============================================================================

def _run_job_single(job_id: str, csv_path: str, csv_content: str, dry_run: bool, flow: str | None = None):
    """Run campaign creation in a single subprocess (background thread)."""
    cmd, flow_used, flow_source = _build_command(csv_path, csv_content, dry_run, flow)

    with job_lock:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["log_lines"] = [f"Flow: {flow_used} ({flow_source})", f"Command: {' '.join(cmd)}"]

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
            jobs[job_id]["processes"] = [proc]

        log_lines: deque[str] = deque(maxlen=500)
        campaign_ids: list[str] = []
        campaigns_created = 0

        for line in proc.stdout:  # type: ignore[union-attr]
            line = line.rstrip()
            log_lines.append(line)
            m = ID_PATTERN.search(line)
            if m:
                campaigns_created += 1
                campaign_ids.append(m.group(1))
            mt = TOTAL_PATTERN.search(line)
            if mt:
                with job_lock:
                    jobs[job_id]["total_campaigns"] = int(mt.group(1))
            mv = VARIANT_TOTAL_PATTERN.search(line)
            if mv:
                with job_lock:
                    jobs[job_id]["total_campaigns"] = int(mv.group(1))
            with job_lock:
                jobs[job_id]["log_lines"] = list(log_lines)
                jobs[job_id]["campaigns_created"] = campaigns_created
                jobs[job_id]["campaign_ids"] = campaign_ids

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


# ============================================================================
# PARALLEL JOB (workers > 1)
# ============================================================================

def _run_job_parallel(job_id: str, csv_path: str, csv_content: str, dry_run: bool,
                      flow: str | None, num_workers: int):
    """Run campaign creation across multiple parallel browser workers."""
    _, flow_used, flow_source = _build_command(csv_path, csv_content, dry_run, flow)
    actual_flow = flow_used

    with job_lock:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["log_lines"] = [
            f"Flow: {flow_used} ({flow_source})",
            f"Parallel workers: {num_workers}",
        ]

    try:
        # --- Phase 1: For multilingual, run translation first, then split output CSV ---
        csv_to_split = csv_content
        actual_csv_path = csv_path

        if actual_flow == "multilingual" and not dry_run:
            with job_lock:
                jobs[job_id]["log_lines"].append("Phase 1: Running translation (create_multilingual.py without --create-campaigns)...")

            params = _extract_multilingual_params(csv_content)
            translate_cmd = [
                sys.executable, str(MULTILINGUAL_SCRIPT),
                "--languages", csv_path,
                "--format", params["ad_format"],
                "--group", params["group"],
                "--live",
                # No --create-campaigns: just translate + generate campaign CSV
            ]

            translate_proc = subprocess.Popen(
                translate_cmd,
                cwd=str(TJ_TOOL_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env={**os.environ, "WORKER_ID": "galactus"},
            )
            with job_lock:
                jobs[job_id]["processes"] = [translate_proc]

            output_csv_path = None
            for line in translate_proc.stdout:  # type: ignore[union-attr]
                line = line.rstrip()
                with job_lock:
                    jobs[job_id]["log_lines"].append(f"[translate] {line}")
                m = CAMPAIGN_CSV_PATTERN.search(line)
                if m:
                    output_csv_path = m.group(1).strip()

            translate_proc.wait()
            if translate_proc.returncode != 0:
                with job_lock:
                    jobs[job_id]["status"] = "failed"
                    jobs[job_id]["error"] = "Translation phase failed"
                return

            if output_csv_path and Path(output_csv_path).exists():
                csv_to_split = Path(output_csv_path).read_text()
                actual_csv_path = output_csv_path
                actual_flow = "standard"  # The output CSV is standard format
                with job_lock:
                    jobs[job_id]["log_lines"].append(f"Phase 1 done. Campaign CSV: {output_csv_path}")
            else:
                with job_lock:
                    jobs[job_id]["log_lines"].append("Warning: No campaign CSV path found in translate output, splitting original CSV")

        # --- Phase 2: Split CSV into worker chunks ---
        chunks = _split_csv_content(csv_to_split, num_workers)
        actual_workers = len(chunks)
        quadrants = _compute_quadrants(actual_workers)

        with job_lock:
            jobs[job_id]["log_lines"].append(f"Split into {actual_workers} worker chunks")

        # Write worker CSV files to same dir as original CSV so relative ad CSV paths resolve
        temp_dir = Path(actual_csv_path).parent
        temp_dir.mkdir(parents=True, exist_ok=True)
        worker_csv_paths: list[Path] = []
        for i, chunk in enumerate(chunks):
            chunk_path = temp_dir / f"temp_batch_galactus_w{i + 1}.csv"
            chunk_path.write_text(chunk)
            worker_csv_paths.append(chunk_path)

        # Setup log files
        LOG_DIR.mkdir(exist_ok=True)
        worker_log_paths: list[Path] = []
        for i in range(actual_workers):
            log_path = LOG_DIR / f"worker_galactus_{i + 1}.log"
            worker_log_paths.append(log_path)

        # --- Phase 3: Launch worker 1 first (normal login), wait for session ---
        session_mtime_before = SESSION_FILE.stat().st_mtime if SESSION_FILE.exists() else 0

        def _build_worker_cmd(worker_idx: int, chunk_csv: Path, quad: dict, use_session: bool) -> list[str]:
            """Build command for a single worker process."""
            if actual_flow == "standard" or actual_flow == "multilingual":
                cmd = [
                    sys.executable, str(STANDARD_SCRIPT),
                    "--input", str(chunk_csv),
                    f"--window-position={quad['x']},{quad['y']}",
                    f"--window-size={quad['w']},{quad['h']}",
                ]
                if use_session:
                    cmd.extend(["--use-session", "--session-file", str(SESSION_FILE)])
                if dry_run:
                    cmd.append("--dry-run")
            elif actual_flow == "v4":
                cmd = [sys.executable, str(V4_SCRIPT), str(chunk_csv), "--live"]
                if dry_run:
                    cmd.append("--dry-run")
            elif actual_flow == "template":
                cmd = [
                    sys.executable, str(TEMPLATE_SCRIPT),
                    "--input", str(chunk_csv),
                ]
                if dry_run:
                    cmd.append("--dry-run")
                else:
                    cmd.extend(["--live", "--no-headless"])
            else:
                cmd = [
                    sys.executable, str(STANDARD_SCRIPT),
                    "--input", str(chunk_csv),
                    f"--window-position={quad['x']},{quad['y']}",
                    f"--window-size={quad['w']},{quad['h']}",
                ]
                if use_session:
                    cmd.extend(["--use-session", "--session-file", str(SESSION_FILE)])
                if dry_run:
                    cmd.append("--dry-run")
            return cmd

        # Launch worker 1 (manual login, no --use-session)
        worker_procs: list[subprocess.Popen] = []
        cmd1 = _build_worker_cmd(0, worker_csv_paths[0], quadrants[0], use_session=False)
        with job_lock:
            jobs[job_id]["log_lines"].append(f"Launching Worker 1 (login): {' '.join(cmd1)}")

        with open(worker_log_paths[0], 'w') as f1:
            proc1 = subprocess.Popen(
                cmd1,
                cwd=str(TJ_TOOL_DIR),
                stdout=f1,
                stderr=subprocess.STDOUT,
                text=True,
                env={**os.environ, "WORKER_ID": "galactus_w1"},
            )
        worker_procs.append(proc1)

        with job_lock:
            jobs[job_id]["processes"] = worker_procs[:]

        # Wait for session file to be updated (login complete)
        if actual_workers > 1:
            with job_lock:
                jobs[job_id]["log_lines"].append("Waiting for Worker 1 to complete login...")

            session_ready = False
            for wait_i in range(100):  # Up to 200 seconds (100 * 2s)
                time.sleep(2)
                # Check if worker 1 already exited (error)
                if proc1.poll() is not None:
                    with job_lock:
                        jobs[job_id]["log_lines"].append(f"Worker 1 exited early (code {proc1.returncode})")
                    break
                # Check if session file was updated
                if SESSION_FILE.exists():
                    current_mtime = SESSION_FILE.stat().st_mtime
                    if current_mtime > session_mtime_before:
                        session_ready = True
                        with job_lock:
                            jobs[job_id]["log_lines"].append("Session file updated — login complete")
                        break

            if not session_ready and proc1.poll() is None:
                with job_lock:
                    jobs[job_id]["log_lines"].append("Warning: Session not detected after 200s, launching remaining workers anyway")

            # --- Phase 4: Launch workers 2-N with --use-session, staggered 2s ---
            for i in range(1, actual_workers):
                cmd_i = _build_worker_cmd(i, worker_csv_paths[i], quadrants[i], use_session=True)
                with job_lock:
                    jobs[job_id]["log_lines"].append(f"Launching Worker {i + 1} (session): {' '.join(cmd_i)}")

                with open(worker_log_paths[i], 'w') as fi:
                    proc_i = subprocess.Popen(
                        cmd_i,
                        cwd=str(TJ_TOOL_DIR),
                        stdout=fi,
                        stderr=subprocess.STDOUT,
                        text=True,
                        env={**os.environ, "WORKER_ID": f"galactus_w{i + 1}"},
                    )
                worker_procs.append(proc_i)

                with job_lock:
                    jobs[job_id]["processes"] = worker_procs[:]

                if i < actual_workers - 1:
                    time.sleep(2)  # Stagger launches

        # --- Phase 5: Monitor all workers ---
        with job_lock:
            jobs[job_id]["log_lines"].append(f"All {actual_workers} workers launched. Monitoring...")

        while True:
            # Check if all processes are done
            statuses = [p.poll() for p in worker_procs]
            all_done = all(s is not None for s in statuses)

            # Aggregate data from log files
            all_campaign_ids: list[str] = []
            all_log_lines: list[str] = []
            total_campaigns_found = 0
            for i, log_path in enumerate(worker_log_paths):
                ids, lines, total = _parse_log_file(log_path)
                all_campaign_ids.extend(ids)
                total_campaigns_found += total
                # Add worker prefix to log lines for interleaved display
                for line in lines[-50:]:  # Last 50 lines per worker
                    all_log_lines.append(f"[W{i + 1}] {line}")

            with job_lock:
                jobs[job_id]["campaign_ids"] = list(dict.fromkeys(all_campaign_ids))  # dedupe preserving order
                jobs[job_id]["campaigns_created"] = len(jobs[job_id]["campaign_ids"])
                if total_campaigns_found > 0:
                    jobs[job_id]["total_campaigns"] = total_campaigns_found
                # Keep initial log lines (flow info, launch info) and append worker logs
                initial_lines = [l for l in jobs[job_id]["log_lines"] if not l.startswith("[W")]
                jobs[job_id]["log_lines"] = initial_lines + all_log_lines[-400:]

            if all_done:
                break

            time.sleep(3)

        # --- Phase 6: Determine final status ---
        return_codes = [p.returncode for p in worker_procs]
        any_succeeded = any(rc == 0 for rc in return_codes)
        all_failed = all(rc != 0 for rc in return_codes)

        with job_lock:
            if all_failed:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = f"All workers failed. Return codes: {return_codes}"
            elif any_succeeded:
                jobs[job_id]["status"] = "completed"
                if not all(rc == 0 for rc in return_codes):
                    failed_workers = [i + 1 for i, rc in enumerate(return_codes) if rc != 0]
                    jobs[job_id]["log_lines"].append(f"Warning: Workers {failed_workers} failed")

        # Cleanup temp CSV files
        for chunk_path in worker_csv_paths:
            try:
                chunk_path.unlink(missing_ok=True)
            except Exception:
                pass

    except Exception as e:
        with job_lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health", response_model=HealthResponse)
def health():
    from worker_server.net_speed import get_speeds

    hostname = socket.gethostname()
    with job_lock:
        active = sum(1 for j in jobs.values() if j["status"] in ("pending", "running"))
    speeds = get_speeds()
    return HealthResponse(
        hostname=hostname,
        active_jobs=active,
        available_ad_csvs=_get_ad_csvs(),
        download_speed=speeds["download_bytes_per_sec"],
        upload_speed=speeds["upload_bytes_per_sec"],
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
    # Check max concurrent jobs (1 logical job at a time)
    with job_lock:
        running = sum(1 for j in jobs.values() if j["status"] in ("pending", "running"))
        if running >= 1:
            raise HTTPException(
                status_code=429,
                detail="Worker is busy. Max 1 concurrent job allowed.",
            )

    job_id = str(uuid.uuid4())
    num_workers = max(1, min(4, req.workers))

    # Write CSV into the appropriate input dir based on flow/format
    # so that relative ad CSV paths (e.g. ads/foo.csv) resolve correctly
    detected_format = _detect_csv_format(req.csv_content)
    explicit_flow = req.flow or detected_format
    if explicit_flow == "template":
        input_dir = TEMPLATE_DIR
    elif explicit_flow == "v4" or detected_format == "v4":
        input_dir = V4_DIR
    elif explicit_flow == "multilingual" or detected_format == "multilingual":
        input_dir = TJ_TOOL_DIR / "data" / "input" / "Multilingual_Campaign_Creation"
    else:
        input_dir = CAMPAIGN_CREATION_DIR
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
            "num_workers": num_workers,
            "campaigns_created": 0,
            "total_campaigns": total_campaigns,
            "campaign_ids": [],
            "log_lines": [],
            "error": None,
            "processes": [],
        }

    # Choose single or parallel execution
    if num_workers <= 1 or req.dry_run:
        target = _run_job_single
        args = (job_id, str(csv_path), req.csv_content, req.dry_run, req.flow)
    else:
        target = _run_job_parallel
        args = (job_id, str(csv_path), req.csv_content, req.dry_run, req.flow, num_workers)

    thread = threading.Thread(target=target, args=args, daemon=True)
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
        campaign_ids=job.get("campaign_ids", []),
        log_lines=job["log_lines"],
        error=job.get("error"),
    )


@app.delete("/jobs/{job_id}")
def cancel_job(job_id: str):
    with job_lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Terminate all worker processes
    processes = job.get("processes", [])
    # Also check legacy single-process field
    if not processes:
        proc = job.get("process")
        if proc:
            processes = [proc]

    terminated = 0
    for proc in processes:
        if proc and proc.poll() is None:
            proc.terminate()
            terminated += 1

    if terminated > 0:
        with job_lock:
            jobs[job_id]["status"] = "cancelled"
        return {"message": f"Job cancelled ({terminated} process(es) terminated)"}
    return {"message": "Job is not running"}
