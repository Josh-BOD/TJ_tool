"""Background daemon that samples network throughput every 5 seconds."""

import threading
import time

import psutil

_lock = threading.Lock()
_prev: dict | None = None
_curr: dict | None = None


def _sample_loop() -> None:
    global _prev, _curr
    while True:
        counters = psutil.net_io_counters()
        now = time.monotonic()
        snapshot = {
            "bytes_sent": counters.bytes_sent,
            "bytes_recv": counters.bytes_recv,
            "time": now,
        }
        with _lock:
            _prev = _curr
            _curr = snapshot
        time.sleep(5)


_thread = threading.Thread(target=_sample_loop, daemon=True)
_thread.start()


def get_speeds() -> dict:
    """Return current download/upload bytes per second."""
    with _lock:
        if _prev is None or _curr is None:
            return {"download_bytes_per_sec": 0.0, "upload_bytes_per_sec": 0.0}
        dt = _curr["time"] - _prev["time"]
        if dt <= 0:
            return {"download_bytes_per_sec": 0.0, "upload_bytes_per_sec": 0.0}
        return {
            "download_bytes_per_sec": (_curr["bytes_recv"] - _prev["bytes_recv"]) / dt,
            "upload_bytes_per_sec": (_curr["bytes_sent"] - _prev["bytes_sent"]) / dt,
        }
