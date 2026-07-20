# core/logger.py
"""
CPU usage logger — samples per-process CPU every `interval` seconds
and writes the top-N processes by load to a timestamped CSV.
"""

import csv
import os
import time
from datetime import datetime

import psutil


def _warm_up_processes() -> dict[int, psutil.Process]:
    """
    Call cpu_percent(interval=None) once on every process to initialise
    psutil's internal per-process CPU counter.  The first call always
    returns 0.0; only subsequent calls return real values.

    Returns a dict of {pid: Process} so the main loop reuses the same
    objects instead of re-enumerating from scratch each tick.
    """
    procs: dict[int, psutil.Process] = {}
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            proc.cpu_percent(interval=None)  # discard — initialises counter
            procs[proc.pid] = proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return procs


def log_cpu_usage(
    interval: float = 5.0,
    duration: float = 60.0,
    top_n: int = 10,
    save_dir: str = "data",
) -> str:
    """
    Log per-process CPU usage to a timestamped CSV file.

    Parameters
    ----------
    interval : float
        Seconds between samples.  Must be > 0.
    duration : float
        Total wall-clock seconds to run the logger.
    top_n : int
        Number of top CPU-consuming processes to record per sample.
    save_dir : str
        Directory where the CSV file will be written.

    Returns
    -------
    str
        Absolute path of the CSV file that was written.

    Notes
    -----
    * A one-interval warm-up sleep is added before the first real sample
      so that psutil's CPU counters have a baseline to diff against.
    * Processes that disappear between warm-up and sampling are silently
      skipped (NoSuchProcess / AccessDenied).
    * The system-wide `cpu_percent` column is the mean across all logical
      cores (consistent with psutil's default behaviour).
    """
    if interval <= 0:
        raise ValueError("interval must be positive")
    if duration <= 0:
        raise ValueError("duration must be positive")

    os.makedirs(save_dir, exist_ok=True)
    session_ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_file = os.path.join(save_dir, f"cpu_log_{session_ts}.csv")

    # --- warm-up: initialise per-process CPU counters ---
    procs = _warm_up_processes()
    time.sleep(interval)  # wait one full interval so diffs are meaningful

    with open(log_file, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["timestamp", "pid", "process_name", "cpu_percent"])

        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            timestamp = datetime.now().isoformat()

            # Re-enumerate to pick up new processes; reuse existing objects
            for proc in psutil.process_iter(["pid", "name"]):
                if proc.pid not in procs:
                    try:
                        proc.cpu_percent(interval=None)  # warm-up new arrival
                        procs[proc.pid] = proc
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

            # Sample CPU for all known processes
            samples: list[tuple[int, str, float]] = []
            dead_pids: list[int] = []
            for pid, proc in procs.items():
                try:
                    cpu = proc.cpu_percent(interval=None)
                    name = proc.info["name"] if "name" in proc.info else proc.name()
                    samples.append((pid, name, cpu))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    dead_pids.append(pid)

            # Evict dead processes so we don't accumulate stale entries
            for pid in dead_pids:
                procs.pop(pid, None)

            # Write top-N by CPU — sort is O(n log n) which is fine here
            samples.sort(key=lambda x: x[2], reverse=True)
            for pid, name, cpu in samples[:top_n]:
                writer.writerow([timestamp, pid, name, round(cpu, 2)])

            time.sleep(interval)

    print(f"✅ CPU usage logged to {log_file}")
    return log_file