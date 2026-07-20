# core/energy.py
"""
Energy estimation from CPU usage logs.

This is the single authoritative implementation.  No other module should
reimplement these calculations — import from here.
"""

from __future__ import annotations

import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum gap between two consecutive samples that is considered "continuous".
# Gaps wider than this are treated as machine-sleep / restart events and are
# excluded from energy accumulation.
MAX_CONTINUOUS_GAP_SECONDS: float = 300.0  # 5 minutes


def load_log(log_path: str) -> pd.DataFrame:
    """
    Read a CPU log CSV and return a clean DataFrame sorted by timestamp.

    Columns expected: timestamp, cpu_percent
    Additional columns (pid, process_name) are dropped if present so the
    returned frame always has exactly: [timestamp, cpu_percent].

    Parameters
    ----------
    log_path : str
        Path to the CSV file produced by logger.py.

    Returns
    -------
    pd.DataFrame
        Columns: timestamp (datetime64), cpu_percent (float).
        Rows are de-duplicated on timestamp and sorted ascending.

    Raises
    ------
    FileNotFoundError
        If log_path does not exist.
    ValueError
        If required columns are missing or the file is empty after cleaning.
    """
    df = pd.read_csv(log_path, usecols=["timestamp", "cpu_percent"], on_bad_lines="skip")

    if df.empty:
        raise ValueError(f"Log file is empty or has no valid rows: {log_path}")

    required = {"timestamp", "cpu_percent"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns {missing} in {log_path}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=False)
    df["cpu_percent"] = pd.to_numeric(df["cpu_percent"], errors="coerce")
    df = df.dropna(subset=["timestamp", "cpu_percent"])
    df = df[df["cpu_percent"].between(0.0, 100.0)]  # sanity-check range
    df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    if df.empty:
        raise ValueError(f"No valid rows remain after cleaning: {log_path}")

    return df


def estimate_energy(
    log_path: str,
    tdp_watts: float = 45.0,
    max_gap_seconds: float = MAX_CONTINUOUS_GAP_SECONDS,
) -> dict:
    """
    Estimate CPU energy consumption from a log file.

    Rather than assuming a fixed sampling interval, this function computes
    the actual time delta between every pair of consecutive rows.  Gaps
    larger than `max_gap_seconds` (machine sleep / restart) are excluded
    from energy accumulation so they don't inflate the estimate.

    Energy model
    ------------
    For each interval i:
        power_i  = (cpu_percent_i / 100) * tdp_watts          [Watts]
        energy_i = power_i * delta_i                           [Joules]

    This is a trapezoidal-style approximation using the *start* sample of
    each interval — conservative and consistent with standard TDP modelling.

    Parameters
    ----------
    log_path : str
        Path to the CPU log CSV.
    tdp_watts : float
        Thermal Design Power of the CPU in watts.
    max_gap_seconds : float
        Gaps larger than this are skipped (not counted as active time).

    Returns
    -------
    dict with keys:
        avg_cpu_percent, max_cpu_percent, min_cpu_percent,
        estimated_energy_joules, estimated_energy_wh,
        active_seconds, total_wall_seconds, skipped_gap_seconds,
        data_points
    """
    df = load_log(log_path)

    if len(df) == 1:
        return {
            "avg_cpu_percent": round(float(df["cpu_percent"].iloc[0]), 2),
            "max_cpu_percent": float(df["cpu_percent"].iloc[0]),
            "min_cpu_percent": float(df["cpu_percent"].iloc[0]),
            "estimated_energy_joules": 0.0,
            "estimated_energy_wh": 0.0,
            "active_seconds": 0.0,
            "total_wall_seconds": 0.0,
            "skipped_gap_seconds": 0.0,
            "data_points": 1,
        }

    # Compute per-row deltas in seconds
    deltas = df["timestamp"].diff().dt.total_seconds()  # NaN for row 0

    total_wall = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).total_seconds()

    energy_joules = 0.0
    active_seconds = 0.0
    skipped_seconds = 0.0

    for i in range(1, len(df)):
        delta = deltas.iloc[i]
        if delta <= 0:
            continue  # clock skew or duplicate — skip
        if delta > max_gap_seconds:
            skipped_seconds += delta
            continue  # machine was asleep / logger was stopped

        power = (df["cpu_percent"].iloc[i - 1] / 100.0) * tdp_watts
        energy_joules += power * delta
        active_seconds += delta

    return {
        "avg_cpu_percent": round(float(df["cpu_percent"].mean()), 2),
        "max_cpu_percent": float(df["cpu_percent"].max()),
        "min_cpu_percent": float(df["cpu_percent"].min()),
        "estimated_energy_joules": round(energy_joules, 4),
        "estimated_energy_wh": round(energy_joules / 3600.0, 6),
        "active_seconds": round(active_seconds, 2),
        "total_wall_seconds": round(total_wall, 2),
        "skipped_gap_seconds": round(skipped_seconds, 2),
        "data_points": len(df),
    }