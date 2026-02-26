"""
FastAPI campaign scraper service.

Provides endpoints to scrape campaign settings from TJ web UI
and push field updates back.

Architecture:
- Browser pool of up to MAX_BROWSERS (4) persistent Playwright instances
- Worker 1 does manual login (reCAPTCHA), saves session to tj_session.json
- Workers 2-4 load saved session via storage_state (no login required)
- Jobs enter a queue and are dispatched to the next free worker
- Workers stay alive between jobs (session reuse, no per-job browser launch)
"""

import logging
import os
import queue
import socket
import sys
import threading
import time
import uuid
from collections import deque
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware

from src.campaign_scraper.models import (
    ScrapeRequest,
    UpdateRequest,
    JobStatusResponse,
    HealthResponse,
    WebhookPayload,
)

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Load .env from TJ_tool root (same as config/config.py)
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [SCRAPER] %(message)s",
)

# ── Config ────────────────────────────────────────────────────────
BEARER_TOKEN = os.environ.get("MBP_WORKER_TOKEN", "")
TJ_USERNAME = os.environ.get("TJ_USERNAME", "")
TJ_PASSWORD = os.environ.get("TJ_PASSWORD", "")
GALACTUS_WEBHOOK_URL = os.environ.get("GALACTUS_WEBHOOK_URL", "")
GALACTUS_WEBHOOK_TOKEN = os.environ.get("MBP_WORKER_TOKEN", "")
MAX_BROWSERS = 4
SESSION_FILE = PROJECT_ROOT / "data" / "session" / "tj_session.json"

# ── App ───────────────────────────────────────────────────────────
app = FastAPI(title="Campaign Scraper Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory job store ───────────────────────────────────────────
jobs: dict[str, dict] = {}
job_lock = threading.Lock()
is_authenticated = False
session_needs_reload = False  # Set by /session endpoint, forces workers to re-auth on next job

# ── Job queue + worker pool ───────────────────────────────────────
# PriorityQueue: items are (priority, sequence, job_dict) tuples
# Lower priority number = processed first (1=create, 2=update, 3=scrape)
job_queue: queue.PriorityQueue = queue.PriorityQueue()
_job_seq = 0  # tiebreaker so same-priority jobs stay FIFO
pool_lock = threading.Lock()
workers_launched = 0  # how many workers have been started total
active_workers = 0    # how many are currently alive
worker_threads: dict[int, threading.Thread] = {}  # worker_id -> thread
pool_disabled = False  # Set True after too many failures; prevents watchdog/scale_pool from restarting
pool_disabled_reason = ""  # Human-readable reason for disabling


# ── Auth dependency ───────────────────────────────────────────────
async def verify_bearer(request: Request):
    if not BEARER_TOKEN:
        return  # No auth configured, allow all
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid bearer token")


# ── Browser worker ────────────────────────────────────────────────
def _worker_loop(worker_id: int, is_first: bool):
    """
    Persistent browser worker. Stays alive pulling jobs from the queue.

    Args:
        worker_id: 1-based worker index
        is_first: If True, does manual login and saves session.
                  If False, waits for session file then loads it.
    """
    global is_authenticated, active_workers, workers_launched, session_needs_reload
    from playwright.sync_api import sync_playwright
    from auth import TJAuthenticator

    prefix = f"[W{worker_id}]"
    logger.info(f"{prefix} Starting browser worker (first={is_first})")

    with pool_lock:
        active_workers += 1

    try:
        with sync_playwright() as pw:
            auth_helper = TJAuthenticator(TJ_USERNAME, TJ_PASSWORD)
            browser = None
            context = None
            reuse_page = None  # page to reuse from login (worker 1 first job)

            def _launch_and_auth() -> bool:
                """Launch browser + authenticate. Returns True on success.

                Priority order:
                1. Load session file (written by /session endpoint or previous login)
                2. manual_login as fallback (worker 1 only, or any worker if no session)
                """
                nonlocal browser, context, reuse_page
                global is_authenticated

                # Close existing browser if any
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass
                reuse_page = None

                browser = pw.chromium.launch(headless=False)

                # Always try session file first (may have been pushed via /session API)
                if SESSION_FILE.exists():
                    logger.info(f"{prefix} Session file found, trying to load...")
                    context = auth_helper.load_session(browser)
                    if context:
                        is_authenticated = True
                        logger.info(f"{prefix} Session loaded successfully")
                        return True
                    else:
                        logger.warning(f"{prefix} Session file exists but load_session failed")

                # No valid session — fall back to manual_login
                logger.info(f"{prefix} No valid session, trying manual login...")
                context = browser.new_context()
                page = context.new_page()
                success = auth_helper.manual_login(page)
                if not success:
                    return False

                auth_helper.save_session(context)
                is_authenticated = True
                logger.info(f"{prefix} Login successful, session saved")
                reuse_page = page
                return True

            # ── Initial auth with retry (4 attempts, 30s between) ─
            if not is_first:
                # Workers 2-N: wait for worker 1 to authenticate first
                logger.info(f"{prefix} Waiting for session file...")
                deadline = time.time() + 180
                while time.time() < deadline:
                    if SESSION_FILE.exists() and is_authenticated:
                        break
                    time.sleep(2)
                else:
                    logger.error(f"{prefix} Timed out waiting for session. Exiting.")
                    return
                time.sleep(worker_id * 1.5)

            auth_success = False
            for attempt in range(1, 5):
                logger.info(f"{prefix} Auth attempt {attempt}/4...")
                try:
                    if _launch_and_auth():
                        auth_success = True
                        break
                except Exception as e:
                    logger.warning(f"{prefix} Auth attempt {attempt} error: {e}")

                if attempt < 4:
                    logger.info(f"{prefix} Auth failed, retrying in 30s...")
                    try:
                        if browser:
                            browser.close()
                            browser = None
                    except Exception:
                        pass
                    reuse_page = None
                    time.sleep(30)

            if not auth_success:
                logger.error(f"{prefix} All 4 auth attempts failed. Worker exiting.")
                try:
                    if browser:
                        browser.close()
                except Exception:
                    pass
                return

            # ── Main job loop (reuse same page/tab between jobs) ─
            last_auth_time = time.time()  # just authenticated
            SESSION_CHECK_INTERVAL = 300  # only check is_logged_in every 5 min
            consecutive_failures = 0

            # Create one persistent page that lives across all jobs.
            # This avoids opening/closing browser windows per campaign.
            persistent_page = reuse_page or context.new_page()
            reuse_page = None

            while True:
                try:
                    queue_entry = job_queue.get(timeout=300)  # 5 min idle timeout
                except queue.Empty:
                    logger.info(f"{prefix} Idle timeout, shutting down")
                    break

                if queue_entry is None:
                    # Poison pill — shutdown signal
                    logger.info(f"{prefix} Received shutdown signal")
                    break

                # Unpack priority tuple: (priority, seq, job_dict)
                if isinstance(queue_entry, tuple):
                    _prio, _seq, job_item = queue_entry
                else:
                    job_item = queue_entry  # backwards compat

                job_id = job_item["job_id"]
                job_type = job_item["job_type"]
                campaign_id = job_item["campaign_id"]
                webhook_url = job_item.get("webhook_url")

                def log(msg: str):
                    logger.info(f"{prefix} [{job_id[:8]}] {msg}")
                    with job_lock:
                        if job_id in jobs:
                            jobs[job_id]["log_lines"].append(f"[W{worker_id}] {msg}")

                # Check if job was cancelled while queued
                with job_lock:
                    if job_id in jobs and jobs[job_id]["status"] == "cancelled":
                        log("Job was cancelled, skipping")
                        job_queue.task_done()
                        continue
                    if job_id in jobs:
                        jobs[job_id]["status"] = "running"

                try:
                    # Ensure persistent page is still usable
                    try:
                        _ = persistent_page.url
                    except Exception:
                        logger.info(f"{prefix} Persistent page crashed, creating new one")
                        persistent_page = context.new_page()

                    page = persistent_page

                    # Verify session if it's been a while OR if /session endpoint pushed fresh cookies
                    needs_check = (time.time() - last_auth_time) > SESSION_CHECK_INTERVAL or session_needs_reload
                    if session_needs_reload:
                        log("Session reload forced by /session push")
                        session_needs_reload = False
                    if needs_check:
                        # Navigate to TJ first — is_logged_in checks the current URL,
                        # so it would always fail on a blank page
                        try:
                            page.goto('https://advertiser.trafficjunky.com/',
                                      wait_until='domcontentloaded', timeout=15000)
                            page.wait_for_timeout(2000)
                        except Exception as nav_err:
                            log(f"Nav check failed: {nav_err}")

                        if auth_helper.is_logged_in(page):
                            last_auth_time = time.time()
                            log("Session still valid")
                        else:
                            is_authenticated = False
                            log("Session expired, re-authenticating...")

                            # Try 1: reload session file (may have been freshly pushed)
                            reauth_ok = False
                            if SESSION_FILE.exists():
                                log("Trying session file first...")
                                try:
                                    old_ctx = context
                                    new_ctx = auth_helper.load_session(browser)
                                    if new_ctx:
                                        # Close old page + context, switch to new
                                        try:
                                            persistent_page.close()
                                        except Exception:
                                            pass
                                        try:
                                            old_ctx.close()
                                        except Exception:
                                            pass
                                        context = new_ctx
                                        persistent_page = context.new_page()
                                        page = persistent_page
                                        page.goto('https://advertiser.trafficjunky.com/',
                                                  wait_until='domcontentloaded', timeout=15000)
                                        page.wait_for_timeout(2000)
                                        if auth_helper.is_logged_in(page):
                                            last_auth_time = time.time()
                                            reauth_ok = True
                                            log("Re-auth via session file successful")
                                        else:
                                            log("Session file loaded but not logged in")
                                    else:
                                        context = old_ctx  # restore if load_session returned None
                                        log("Session file load returned None")
                                except Exception as sess_err:
                                    log(f"Session file re-auth error: {sess_err}")

                            # Try 2: manual_login as last resort (new browser)
                            if not reauth_ok:
                                for attempt in range(1, 5):
                                    log(f"Re-auth manual_login attempt {attempt}/4...")
                                    try:
                                        persistent_page.close()
                                    except Exception:
                                        pass
                                    try:
                                        context.close()
                                    except Exception:
                                        pass
                                    try:
                                        browser.close()
                                    except Exception:
                                        pass
                                    if attempt > 1:
                                        time.sleep(30)
                                    browser = pw.chromium.launch(headless=False)
                                    context = browser.new_context()
                                    persistent_page = context.new_page()
                                    page = persistent_page
                                    try:
                                        success = auth_helper.manual_login(page)
                                        if success:
                                            auth_helper.save_session(context)
                                            is_authenticated = True
                                            reauth_ok = True
                                            last_auth_time = time.time()
                                            log("Re-auth via manual_login successful")
                                            break
                                        else:
                                            log(f"Re-auth attempt {attempt} failed")
                                    except Exception as auth_err:
                                        log(f"Re-auth attempt {attempt} error: {auth_err}")

                            if not reauth_ok:
                                raise RuntimeError("All re-auth attempts failed")

                    log(f"Starting {job_type} for campaign {campaign_id}")

                    if job_type == "scrape":
                        from src.campaign_scraper.reader import scrape_campaign
                        result = scrape_campaign(page, campaign_id)

                        with job_lock:
                            if job_id in jobs:
                                jobs[job_id]["status"] = "completed"
                                jobs[job_id]["result"] = result.get("fields")
                                jobs[job_id]["ads"] = result.get("ads")
                                jobs[job_id]["completed_at"] = time.time()

                        log(f"Scrape completed: {len(result.get('fields', {}))} fields, {len(result.get('ads', []))} ads")

                        _send_webhook(webhook_url, WebhookPayload(
                            job_id=job_id,
                            campaign_id=campaign_id,
                            status="completed",
                            job_type="scrape",
                            result=result.get("fields"),
                            ads=result.get("ads"),
                        ))

                    elif job_type == "scrape-cpm":
                        from src.campaign_scraper.cpm_reader import scrape_cpm_placements
                        result = scrape_cpm_placements(page, campaign_id)

                        with job_lock:
                            if job_id in jobs:
                                jobs[job_id]["status"] = "completed"
                                jobs[job_id]["result"] = result
                                jobs[job_id]["completed_at"] = time.time()

                        log(f"CPM collect completed: {result.get('source_count', 0)} placements")

                        _send_webhook(webhook_url, WebhookPayload(
                            job_id=job_id,
                            campaign_id=campaign_id,
                            status="completed",
                            job_type="scrape-cpm",
                            result=result,
                        ))

                    elif job_type == "update":
                        from src.campaign_scraper.writer import update_campaign
                        from src.campaign_scraper.reader import scrape_campaign

                        update_fields = job_item["fields"]
                        dry_run = job_item.get("dry_run", False)

                        update_result = update_campaign(page, campaign_id, update_fields, dry_run=dry_run)
                        log(f"Updated pages: {update_result['updated_pages']}, fields: {update_result['fields_applied']}")

                        if not dry_run:
                            log("Re-scraping to verify changes...")
                            result = scrape_campaign(page, campaign_id)
                        else:
                            result = {"fields": {}, "ads": []}

                        with job_lock:
                            if job_id in jobs:
                                jobs[job_id]["status"] = "completed"
                                jobs[job_id]["result"] = result.get("fields")
                                jobs[job_id]["ads"] = result.get("ads")
                                jobs[job_id]["completed_at"] = time.time()

                        log("Update completed")

                        _send_webhook(webhook_url, WebhookPayload(
                            job_id=job_id,
                            campaign_id=campaign_id,
                            status="completed",
                            job_type="update",
                            result=result.get("fields"),
                            ads=result.get("ads"),
                        ))

                    consecutive_failures = 0

                except Exception as e:
                    error_msg = str(e)
                    logger.exception(f"{prefix} Job {job_id} failed: {error_msg}")
                    with job_lock:
                        if job_id in jobs:
                            jobs[job_id]["status"] = "failed"
                            jobs[job_id]["error"] = error_msg
                            jobs[job_id]["completed_at"] = time.time()

                    log(f"FAILED: {error_msg}")

                    _send_webhook(webhook_url, WebhookPayload(
                        job_id=job_id,
                        campaign_id=campaign_id,
                        status="failed",
                        job_type=job_type,
                        error=error_msg,
                    ))

                    consecutive_failures += 1
                    if consecutive_failures >= 5:
                        global pool_disabled, pool_disabled_reason
                        pool_disabled = True
                        pool_disabled_reason = f"5 consecutive failures (last: {error_msg[:100]})"
                        logger.error(f"{prefix} Too many consecutive failures, disabling pool and shutting down")
                        break

                    # If a job crashed the page, create a fresh one for the next job
                    try:
                        _ = persistent_page.url
                    except Exception:
                        logger.info(f"{prefix} Page crashed after failure, creating new one")
                        try:
                            persistent_page = context.new_page()
                        except Exception:
                            pass

                finally:
                    # Do NOT close the page — reuse it for the next job
                    job_queue.task_done()

            # Cleanup — close persistent page on shutdown
            try:
                persistent_page.close()
            except Exception:
                pass

            # Cleanup
            try:
                context.close()
            except Exception:
                pass
            browser.close()
            logger.info(f"{prefix} Browser closed, worker exiting")

    except Exception as e:
        logger.exception(f"{prefix} Worker crashed: {e}")
    finally:
        with pool_lock:
            active_workers -= 1
            if worker_id == 1:
                logger.warning(f"{prefix} Worker 1 (auth worker) has stopped — next _scale_pool call will restart it")
            # If all workers have died, reset so new jobs can spawn fresh workers
            if active_workers == 0:
                workers_launched = 0
                is_authenticated = False
        logger.info(f"{prefix} Worker stopped (active={active_workers}, launched={workers_launched})")


def _worker1_alive() -> bool:
    """Check if worker 1's thread is still running (must hold pool_lock)."""
    t = worker_threads.get(1)
    return t is not None and t.is_alive()


def _scale_pool():
    """
    Scale the worker pool based on pending queue size.
    - 1-3 jobs: 1 browser (worker 1 handles sequentially)
    - 4+ jobs: scale up to MAX_BROWSERS (4) for parallel scraping

    Handles worker 1 dying: if worker 1 is dead, reset pool state
    and restart with a fresh worker 1 (needed for auth).
    """
    global workers_launched, is_authenticated

    with pool_lock:
        # If pool is disabled (too many failures), don't start new workers
        if pool_disabled:
            logger.debug("Pool is disabled, not scaling")
            return

        pending = job_queue.qsize() + 1  # +1 for the job about to be enqueued

        # Clean up dead worker threads
        dead_ids = [wid for wid, t in worker_threads.items() if not t.is_alive()]
        for wid in dead_ids:
            del worker_threads[wid]

        # If worker 1 is dead, we need to restart from scratch
        # Workers 2-4 depend on worker 1 for auth/session
        if workers_launched > 0 and not _worker1_alive():
            logger.warning(f"Worker 1 is dead (was launched={workers_launched}, active={active_workers}). Resetting pool.")
            workers_launched = 0
            is_authenticated = False

        if workers_launched == 0:
            # Always start worker 1
            desired = 1
        elif pending >= 4:
            # Scale to full pool when 4+ jobs pending
            desired = MAX_BROWSERS
        else:
            # 1-3 jobs: worker 1 handles them sequentially
            desired = workers_launched

        to_start = desired - workers_launched

        if to_start <= 0:
            return

        logger.info(f"Scaling pool: {workers_launched} -> {workers_launched + to_start} workers (pending={pending})")

        for _ in range(to_start):
            worker_id = workers_launched + 1
            is_first = workers_launched == 0
            workers_launched += 1

            t = threading.Thread(
                target=_worker_loop,
                args=(worker_id, is_first),
                daemon=True,
                name=f"scraper-worker-{worker_id}",
            )
            worker_threads[worker_id] = t
            t.start()

            if is_first:
                time.sleep(0.5)
            else:
                time.sleep(0.2)


def _send_webhook(webhook_url: str | None, payload: WebhookPayload):
    """POST webhook to Galactus backend."""
    url = webhook_url or GALACTUS_WEBHOOK_URL
    if not url:
        logger.info("No webhook URL configured, skipping callback")
        return

    try:
        headers = {"Content-Type": "application/json"}
        if GALACTUS_WEBHOOK_TOKEN:
            headers["Authorization"] = f"Bearer {GALACTUS_WEBHOOK_TOKEN}"

        resp = requests.post(url, json=payload.model_dump(), headers=headers, timeout=10)
        logger.info(f"Webhook sent to {url}: {resp.status_code}")
    except Exception as e:
        logger.warning(f"Webhook failed: {e}")


def _active_job_count() -> int:
    with job_lock:
        return sum(1 for j in jobs.values() if j["status"] in ("pending", "running"))


def _queued_job_count() -> int:
    return job_queue.qsize()


# ── Pool watchdog ────────────────────────────────────────────────
def _pool_watchdog():
    """
    Periodically check pool health. If worker 1 is dead but jobs
    are still queued, trigger _scale_pool to restart it.
    Respects pool_disabled — won't restart if pool is disabled.
    """
    while True:
        time.sleep(15)
        try:
            if pool_disabled:
                # Pool is disabled — drain any remaining queued jobs as cancelled
                drained = 0
                while not job_queue.empty():
                    try:
                        entry = job_queue.get_nowait()
                        if isinstance(entry, tuple):
                            _, _, job_item = entry
                        else:
                            job_item = entry
                        with job_lock:
                            jid = job_item.get("job_id", "")
                            if jid in jobs and jobs[jid]["status"] == "pending":
                                jobs[jid]["status"] = "cancelled"
                                jobs[jid]["error"] = "Pool disabled due to consecutive failures"
                                jobs[jid]["completed_at"] = time.time()
                        job_queue.task_done()
                        drained += 1
                    except queue.Empty:
                        break
                if drained > 0:
                    logger.info(f"Watchdog: drained {drained} jobs while pool disabled")
                continue

            queued = job_queue.qsize()
            if queued > 0:
                with pool_lock:
                    if workers_launched > 0 and not _worker1_alive():
                        logger.warning(f"Watchdog: worker 1 dead with {queued} queued jobs, triggering pool restart")
                # Call _scale_pool outside pool_lock (it acquires it internally)
                _scale_pool()
        except Exception as e:
            logger.warning(f"Watchdog error: {e}")


_watchdog_thread = threading.Thread(target=_pool_watchdog, daemon=True, name="pool-watchdog")
_watchdog_thread.start()


# ── Endpoints ─────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        hostname=socket.gethostname(),
        active_jobs=_active_job_count(),
        authenticated=is_authenticated,
        pool_disabled=pool_disabled,
        pool_disabled_reason=pool_disabled_reason,
        queued_jobs=_queued_job_count(),
    )


@app.post("/scrape", response_model=JobStatusResponse, dependencies=[Depends(verify_bearer)])
async def scrape(req: ScrapeRequest):
    if pool_disabled:
        raise HTTPException(status_code=503, detail=f"Pool disabled: {pool_disabled_reason}. Push a fresh session or call /reset first.")

    job_id = str(uuid.uuid4())
    webhook_url = req.webhook_url

    with job_lock:
        jobs[job_id] = {
            "status": "pending",
            "job_type": "scrape",
            "campaign_id": req.campaign_id,
            "result": None,
            "ads": None,
            "error": None,
            "log_lines": deque(maxlen=200),
            "created_at": time.time(),
            "completed_at": None,
        }

    # Enqueue job and ensure pool is running
    global _job_seq
    _scale_pool()
    _job_seq += 1
    job_queue.put((req.priority, _job_seq, {
        "job_id": job_id,
        "job_type": "scrape",
        "campaign_id": req.campaign_id,
        "webhook_url": webhook_url,
    }))

    return JobStatusResponse(
        job_id=job_id,
        status="pending",
        job_type="scrape",
        campaign_id=req.campaign_id,
    )


@app.post("/scrape-cpm", response_model=JobStatusResponse, dependencies=[Depends(verify_bearer)])
async def scrape_cpm(req: ScrapeRequest):
    if pool_disabled:
        raise HTTPException(status_code=503, detail=f"Pool disabled: {pool_disabled_reason}. Push a fresh session or call /reset first.")

    job_id = str(uuid.uuid4())
    webhook_url = req.webhook_url

    with job_lock:
        jobs[job_id] = {
            "status": "pending",
            "job_type": "scrape-cpm",
            "campaign_id": req.campaign_id,
            "result": None,
            "ads": None,
            "error": None,
            "log_lines": deque(maxlen=200),
            "created_at": time.time(),
            "completed_at": None,
        }

    # Enqueue job and ensure pool is running
    global _job_seq
    _scale_pool()
    _job_seq += 1
    job_queue.put((req.priority, _job_seq, {
        "job_id": job_id,
        "job_type": "scrape-cpm",
        "campaign_id": req.campaign_id,
        "webhook_url": webhook_url,
    }))

    return JobStatusResponse(
        job_id=job_id,
        status="pending",
        job_type="scrape-cpm",
        campaign_id=req.campaign_id,
    )


@app.post("/update", response_model=JobStatusResponse, dependencies=[Depends(verify_bearer)])
async def update(req: UpdateRequest):
    if pool_disabled:
        raise HTTPException(status_code=503, detail=f"Pool disabled: {pool_disabled_reason}. Push a fresh session or call /reset first.")

    global _job_seq
    job_id = str(uuid.uuid4())
    webhook_url = req.webhook_url

    with job_lock:
        jobs[job_id] = {
            "status": "pending",
            "job_type": "update",
            "campaign_id": req.campaign_id,
            "update_fields": req.fields,
            "dry_run": req.dry_run,
            "result": None,
            "ads": None,
            "error": None,
            "log_lines": deque(maxlen=200),
            "created_at": time.time(),
            "completed_at": None,
        }

    _scale_pool()
    _job_seq += 1
    job_queue.put((req.priority, _job_seq, {
        "job_id": job_id,
        "job_type": "update",
        "campaign_id": req.campaign_id,
        "fields": req.fields,
        "dry_run": req.dry_run,
        "webhook_url": webhook_url,
    }))

    return JobStatusResponse(
        job_id=job_id,
        status="pending",
        job_type="update",
        campaign_id=req.campaign_id,
    )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse, dependencies=[Depends(verify_bearer)])
async def get_job(job_id: str):
    with job_lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        job_type=job.get("job_type", "scrape"),
        campaign_id=job.get("campaign_id", ""),
        result=job.get("result"),
        ads=job.get("ads"),
        error=job.get("error"),
        log_lines=list(job.get("log_lines", [])),
    )


@app.delete("/jobs/{job_id}", dependencies=[Depends(verify_bearer)])
async def cancel_job(job_id: str):
    with job_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job["status"] in ("pending", "running"):
            job["status"] = "cancelled"
            job["completed_at"] = time.time()

    return {"success": True, "job_id": job_id, "status": "cancelled"}


@app.post("/session", dependencies=[Depends(verify_bearer)])
async def inject_session(request: Request):
    """
    Accept a Playwright storageState (cookies + origins) and write
    it to the session file. Restarts the browser pool so workers
    pick up the fresh session on their next auth cycle.
    """
    import json

    try:
        body = await request.json()
        cookies = body.get("cookies", [])

        if not cookies:
            raise HTTPException(status_code=400, detail="No cookies provided")

        # Write storageState to session file
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SESSION_FILE, "w") as f:
            json.dump(body, f, indent=2)

        logger.info(f"Session injected: {len(cookies)} cookies written to {SESSION_FILE}")

        # Mark as authenticated and force workers to reload session on next job
        global is_authenticated, pool_disabled, pool_disabled_reason, session_needs_reload
        is_authenticated = True
        session_needs_reload = True

        # Clear pool_disabled — fresh session means we should try again
        if pool_disabled:
            logger.info("Session push clearing pool_disabled state")
            pool_disabled = False
            pool_disabled_reason = ""

        return {
            "success": True,
            "message": f"Session injected with {len(cookies)} cookies",
            "cookie_count": len(cookies),
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Session injection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clear-queue", dependencies=[Depends(verify_bearer)])
async def clear_queue():
    """Cancel all pending jobs and drain the queue."""
    cancelled_count = 0
    # Drain the queue
    drained = 0
    while not job_queue.empty():
        try:
            job_queue.get_nowait()
            job_queue.task_done()
            drained += 1
        except queue.Empty:
            break

    # Cancel all pending jobs in-memory
    with job_lock:
        for job_id, job in jobs.items():
            if job["status"] == "pending":
                job["status"] = "cancelled"
                job["completed_at"] = time.time()
                cancelled_count += 1

    return {"success": True, "cancelled": cancelled_count, "drained_from_queue": drained}


# ── Relogin state ────────────────────────────────────────────────
_relogin_lock = threading.Lock()
_relogin_status: dict = {"state": "idle"}  # idle | running | success | failed


def _relogin_thread():
    """Background thread: launch a fresh browser, manual_login(), save session."""
    global is_authenticated, pool_disabled, pool_disabled_reason, session_needs_reload, _relogin_status

    try:
        from playwright.sync_api import sync_playwright
        from auth import TJAuthenticator

        auth_helper = TJAuthenticator(TJ_USERNAME, TJ_PASSWORD)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            logger.info("[RELOGIN] Starting manual_login()...")
            success = auth_helper.manual_login(page)

            if success:
                auth_helper.save_session(context)
                is_authenticated = True
                session_needs_reload = True

                if pool_disabled:
                    logger.info("[RELOGIN] Clearing pool_disabled state")
                    pool_disabled = False
                    pool_disabled_reason = ""

                with _relogin_lock:
                    _relogin_status = {"state": "success", "message": "Relogin successful, session saved"}
                logger.info("[RELOGIN] manual_login() succeeded, session saved")
            else:
                with _relogin_lock:
                    _relogin_status = {"state": "failed", "error": "manual_login() returned False"}
                logger.warning("[RELOGIN] manual_login() returned False")

            try:
                page.close()
                context.close()
                browser.close()
            except Exception:
                pass

    except Exception as e:
        logger.exception(f"[RELOGIN] Failed: {e}")
        with _relogin_lock:
            _relogin_status = {"state": "failed", "error": str(e)}


@app.post("/relogin", dependencies=[Depends(verify_bearer)])
async def relogin():
    """
    Trigger a fresh manual_login() in a background thread.
    Returns immediately. Poll /relogin-status for result.
    """
    global _relogin_status

    with _relogin_lock:
        if _relogin_status.get("state") == "running":
            return {"status": "already_running", "message": "Relogin already in progress"}

        _relogin_status = {"state": "running"}

    t = threading.Thread(target=_relogin_thread, daemon=True, name="relogin-worker")
    t.start()

    return {"status": "relogin_started", "message": "Relogin initiated in background (~20-30s)"}


@app.get("/relogin-status", dependencies=[Depends(verify_bearer)])
async def relogin_status():
    """Check the result of the last /relogin call."""
    with _relogin_lock:
        return _relogin_status.copy()


@app.post("/reset", dependencies=[Depends(verify_bearer)])
async def reset_pool():
    """
    Hard reset: drain queue, cancel all jobs, kill all browser workers,
    clear pool_disabled state, and reset pool counters.
    Workers will get a poison pill and shut down their browsers.
    Next incoming job will start a fresh worker from scratch.
    """
    global pool_disabled, pool_disabled_reason, is_authenticated, workers_launched

    # 1. Drain the queue
    drained = 0
    while not job_queue.empty():
        try:
            job_queue.get_nowait()
            job_queue.task_done()
            drained += 1
        except queue.Empty:
            break

    # 2. Send poison pills to kill all active workers
    pills_sent = 0
    with pool_lock:
        alive_count = sum(1 for t in worker_threads.values() if t.is_alive())
        for _ in range(alive_count):
            job_queue.put(None)  # poison pill
            pills_sent += 1

    # 3. Cancel all pending/running jobs in-memory
    cancelled = 0
    with job_lock:
        for job_id, job in jobs.items():
            if job["status"] in ("pending", "running"):
                job["status"] = "cancelled"
                job["error"] = "Pool reset requested"
                job["completed_at"] = time.time()
                cancelled += 1

    # 4. Clear disabled state
    was_disabled = pool_disabled
    pool_disabled = False
    pool_disabled_reason = ""
    is_authenticated = False

    logger.info(f"Pool reset: drained={drained}, cancelled={cancelled}, pills_sent={pills_sent}, was_disabled={was_disabled}")

    return {
        "success": True,
        "drained": drained,
        "cancelled": cancelled,
        "workers_killed": pills_sent,
        "was_disabled": was_disabled,
        "message": f"Pool reset complete. {pills_sent} workers will shut down. Next job starts fresh.",
    }
