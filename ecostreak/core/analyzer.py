
# core/analyzer.py
"""
CPU log analysis: summary statistics, streak detection, and process attribution.
"""
 
from __future__ import annotations
 
from typing import Any
import pandas as pd
 
from ecostreak.core.energy import load_log
from ecostreak.core.streak import Streak, detect_streaks, streaks_to_dataframe
 
 
def analyze_usage(
    log_path: str,
    threshold: float = 70.0,
) -> dict[str, Any]:
    """
    Return a full analysis summary for a CPU log file.
 
    Parameters
    ----------
    log_path : str
        Path to the CSV produced by logger.py.
    threshold : float
        Percentage above which CPU is considered "high".
 
    Returns
    -------
    dict with keys:
        data_points, avg_cpu, peak_cpu, min_cpu,
        pct_time_above_threshold,
        streaks (list[dict]),
        streak_count, total_streak_seconds, longest_streak_seconds
    """
    df = load_log(log_path)
 
    above = df["cpu_percent"] >= threshold
    pct_above = round(float(above.mean()) * 100, 2)
 
    streaks: list[Streak] = detect_streaks(df, threshold=threshold)
    streak_dicts = [s.to_dict() for s in streaks]
    total_streak_s = sum(s.duration_seconds for s in streaks)
    longest_streak_s = max((s.duration_seconds for s in streaks), default=0.0)
 
    return {
        "data_points": len(df),
        "avg_cpu": round(float(df["cpu_percent"].mean()), 2),
        "peak_cpu": float(df["cpu_percent"].max()),
        "min_cpu": float(df["cpu_percent"].min()),
        "pct_time_above_threshold": pct_above,
        "threshold_used": threshold,
        "streaks": streak_dicts,
        "streak_count": len(streaks),
        "total_streak_seconds": round(total_streak_s, 2),
        "longest_streak_seconds": round(longest_streak_s, 2),
    }
 
 
def detect_cpu_streaks(
    df: pd.DataFrame,
    threshold: float = 70.0,
) -> pd.DataFrame:
    """
    Detect CPU streaks from an already-loaded DataFrame.
 
    Parameters
    ----------
    df : pd.DataFrame
        Columns: timestamp (datetime64), cpu_percent (float).
    threshold : float
        High-CPU threshold.
 
    Returns
    -------
    pd.DataFrame
        One row per streak. Empty DataFrame (correct schema) if none found.
    """
    streaks = detect_streaks(df, threshold=threshold)
    return streaks_to_dataframe(streaks)
 
 
def top_processes_during_streaks(
    log_path: str,
    streaks: list[Streak],
    top_n: int = 5,
) -> pd.DataFrame:
    """
    Identify which processes were running during high-CPU streak windows.
 
    This function reads the raw per-process log (which must contain columns
    pid, process_name, cpu_percent, timestamp) and filters rows that fall
    within any detected streak window. It then aggregates by process name
    to show which applications contributed most to high-load periods.
 
    Parameters
    ----------
    log_path : str
        Path to the CSV produced by logger.py.
        Must contain columns: timestamp, pid, process_name, cpu_percent.
    streaks : list[Streak]
        Streak objects from detect_streaks(). If empty, returns empty DataFrame.
    top_n : int
        How many top processes to return.
 
    Returns
    -------
    pd.DataFrame
        Columns: process_name, avg_cpu_during_streak, peak_cpu, appearances, streak_share_pct
        Sorted by avg_cpu_during_streak descending.
        Empty DataFrame if no streaks or process_name column missing.
 
    Notes
    -----
    "appearances" = number of samples where this process appeared during any streak.
    "streak_share_pct" = what % of all streak-window samples this process appeared in.
 
    Why this matters in interviews
    ------------------------------
    This is the function that answers "which app wasted your energy?"
    It turns raw CPU numbers into actionable insight: Chrome caused 3 of 4 streaks.
    """
    if not streaks:
        return pd.DataFrame(columns=[
            "process_name", "avg_cpu_during_streak",
            "peak_cpu", "appearances", "streak_share_pct"
        ])
 
    # Read full log — need process_name column
    try:
        df = pd.read_csv(log_path, on_bad_lines="skip")
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    except Exception as e:
        raise ValueError(f"Failed to read log for process attribution: {e}")
 
    if "process_name" not in df.columns:
        # Log was written in system-wide mode (no per-process column)
        return pd.DataFrame(columns=[
            "process_name", "avg_cpu_during_streak",
            "peak_cpu", "appearances", "streak_share_pct"
        ])
 
    df["cpu_percent"] = pd.to_numeric(df["cpu_percent"], errors="coerce")
    df = df.dropna(subset=["timestamp", "cpu_percent", "process_name"])
 
    # Build a boolean mask: is this row's timestamp inside ANY streak window?
    # O(n * k) where k = number of streaks — acceptable since k is small (usually < 20)
    in_streak_mask = pd.Series(False, index=df.index)
    for streak in streaks:
        in_window = (df["timestamp"] >= streak.start_time) & (df["timestamp"] <= streak.end_time)
        in_streak_mask = in_streak_mask | in_window
 
    streak_df = df[in_streak_mask].copy()
 
    if streak_df.empty:
        return pd.DataFrame(columns=[
            "process_name", "avg_cpu_during_streak",
            "peak_cpu", "appearances", "streak_share_pct"
        ])
 
    total_streak_samples = len(streak_df)
 
    # Aggregate per process
    grouped = streak_df.groupby("process_name")["cpu_percent"].agg(
        avg_cpu_during_streak="mean",
        peak_cpu="max",
        appearances="count",
    ).reset_index()
 
    grouped["streak_share_pct"] = (
        grouped["appearances"] / total_streak_samples * 100
    ).round(1)
    grouped["avg_cpu_during_streak"] = grouped["avg_cpu_during_streak"].round(2)
    grouped["peak_cpu"] = grouped["peak_cpu"].round(2)
 
    result = (
        grouped
        .sort_values("avg_cpu_during_streak", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
 
    return result
 
 
def summarize_by_hour(log_path: str) -> pd.DataFrame:
    """
    Aggregate CPU usage statistics by hour-of-day.
 
    Useful for identifying which hours of the day are consistently
    high-load vs idle.
 
    Returns
    -------
    pd.DataFrame
        Index: hour (0–23).
        Columns: avg_cpu, max_cpu, sample_count.
    """
    df = load_log(log_path)
    df["hour"] = df["timestamp"].dt.hour
    grouped = df.groupby("hour")["cpu_percent"].agg(
        avg_cpu="mean", max_cpu="max", sample_count="count"
    )
    grouped["avg_cpu"] = grouped["avg_cpu"].round(2)
    return grouped