# core/streak.py
"""
CPU usage streak detection.

A "streak" is a maximal contiguous sequence of samples where
cpu_percent >= threshold, with no inter-sample gap wider than
MAX_STREAK_GAP_SECONDS (to avoid a machine-sleep stitching two
unrelated high-load episodes into one phantom streak).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pandas as pd

from ecostreak.core.energy import load_log

# A gap wider than this breaks a streak even if both boundary samples
# are above the threshold.
MAX_STREAK_GAP_SECONDS: float = 120.0


@dataclass
class Streak:
    """Represents one continuous high-CPU episode."""

    start_time: pd.Timestamp
    end_time: pd.Timestamp
    duration_seconds: float
    avg_cpu: float
    peak_cpu: float
    sample_count: int

    def to_dict(self) -> dict:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": round(self.duration_seconds, 2),
            "avg_cpu": round(self.avg_cpu, 2),
            "peak_cpu": round(self.peak_cpu, 2),
            "sample_count": self.sample_count,
        }


def detect_streaks(
    df: pd.DataFrame,
    threshold: float = 70.0,
    max_gap_seconds: float = MAX_STREAK_GAP_SECONDS,
) -> List[Streak]:
    """
    Detect CPU usage streaks in a time-ordered DataFrame.

    Algorithm: single O(n) pass.
    - Walk rows in order.
    - When a row crosses above `threshold`, open a streak accumulator.
    - While consecutive rows stay above threshold AND the inter-sample gap
      is within `max_gap_seconds`, extend the accumulator.
    - The moment a row drops below threshold OR a gap is too wide, close
      the current streak and record it.

    Parameters
    ----------
    df : pd.DataFrame
        Must have columns: timestamp (datetime64), cpu_percent (float).
        Must be sorted ascending by timestamp (load_log guarantees this).
    threshold : float
        cpu_percent value that must be met or exceeded to count as "in streak".
    max_gap_seconds : float
        Maximum inter-sample gap allowed within a streak.  Wider gaps break
        the streak regardless of CPU values on either side.

    Returns
    -------
    List[Streak]
        Streaks ordered by start_time.  Empty list if none found.

    Edge cases
    ----------
    * Empty DataFrame → empty list.
    * Single row above threshold → streak of duration 0.0 s.
    * All rows below threshold → empty list.
    * Gap > max_gap_seconds between two above-threshold rows → two separate streaks.
    """
    if df.empty:
        return []

    required = {"timestamp", "cpu_percent"}
    if not required.issubset(df.columns):
        raise ValueError(f"DataFrame must contain columns: {required}")

    streaks: List[Streak] = []

    # Accumulator state
    in_streak: bool = False
    streak_start: pd.Timestamp | None = None
    streak_samples: list[float] = []
    streak_prev_time: pd.Timestamp | None = None

    def _close_streak(end_time: pd.Timestamp) -> None:
        """Finalise and record the current open streak."""
        nonlocal in_streak, streak_start, streak_samples, streak_prev_time
        duration = (end_time - streak_start).total_seconds()
        streaks.append(
            Streak(
                start_time=streak_start,
                end_time=end_time,
                duration_seconds=duration,
                avg_cpu=sum(streak_samples) / len(streak_samples),
                peak_cpu=max(streak_samples),
                sample_count=len(streak_samples),
            )
        )
        in_streak = False
        streak_start = None
        streak_samples = []
        streak_prev_time = None

    for _, row in df.iterrows():
        ts: pd.Timestamp = row["timestamp"]
        cpu: float = float(row["cpu_percent"])
        above: bool = cpu >= threshold

        if in_streak:
            gap = (ts - streak_prev_time).total_seconds()

            if gap > max_gap_seconds:
                # Timestamp gap breaks the streak — close with the last good time
                _close_streak(streak_prev_time)
                # Start fresh if this sample is also above threshold
                if above:
                    in_streak = True
                    streak_start = ts
                    streak_samples = [cpu]
                    streak_prev_time = ts
            elif above:
                # Normal extension
                streak_samples.append(cpu)
                streak_prev_time = ts
            else:
                # Dropped below threshold — close streak at previous time
                _close_streak(streak_prev_time)
        else:
            if above:
                in_streak = True
                streak_start = ts
                streak_samples = [cpu]
                streak_prev_time = ts

    # Close any streak still open at end of data
    if in_streak:
        _close_streak(streak_prev_time)

    return streaks


def detect_streaks_from_file(
    log_path: str,
    threshold: float = 70.0,
    max_gap_seconds: float = MAX_STREAK_GAP_SECONDS,
) -> List[Streak]:
    """
    Convenience wrapper: load a log file and return its streaks.

    Parameters
    ----------
    log_path : str
        Path to CSV produced by logger.py.
    threshold : float
        High-CPU threshold in percent.
    max_gap_seconds : float
        Gap tolerance within a streak.

    Returns
    -------
    List[Streak]
    """
    df = load_log(log_path)
    return detect_streaks(df, threshold=threshold, max_gap_seconds=max_gap_seconds)


def streaks_to_dataframe(streaks: List[Streak]) -> pd.DataFrame:
    """
    Convert a list of Streak objects to a tidy DataFrame.

    Returns an empty DataFrame with the correct schema if `streaks` is empty.
    """
    schema = {
        "start_time": pd.Series(dtype="datetime64[ns]"),
        "end_time": pd.Series(dtype="datetime64[ns]"),
        "duration_seconds": pd.Series(dtype="float64"),
        "avg_cpu": pd.Series(dtype="float64"),
        "peak_cpu": pd.Series(dtype="float64"),
        "sample_count": pd.Series(dtype="int64"),
    }
    if not streaks:
        return pd.DataFrame(schema)

    records = [s.to_dict() for s in streaks]
    df = pd.DataFrame(records)
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])
    return df