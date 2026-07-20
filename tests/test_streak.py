# tests/test_streak.py
"""
Unit tests for streak detection.

All tests use synthetic DataFrames — no file I/O.
"""

import pandas as pd
import pytest

from ecostreak.core.streak import detect_streaks, streaks_to_dataframe


def _make_df(timestamps: list[str], cpu: list[float]) -> pd.DataFrame:
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps),
        "cpu_percent": cpu,
    })
    return df.sort_values("timestamp").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_dataframe_returns_empty_list():
    df = pd.DataFrame({"timestamp": pd.Series(dtype="datetime64[ns]"),
                       "cpu_percent": pd.Series(dtype="float64")})
    assert detect_streaks(df) == []


def test_single_row_above_threshold():
    df = _make_df(["2025-01-01 10:00:00"], [80.0])
    streaks = detect_streaks(df, threshold=70.0)
    assert len(streaks) == 1
    assert streaks[0].duration_seconds == 0.0
    assert streaks[0].peak_cpu == 80.0


def test_single_row_below_threshold():
    df = _make_df(["2025-01-01 10:00:00"], [50.0])
    assert detect_streaks(df, threshold=70.0) == []


def test_all_below_threshold():
    df = _make_df(
        ["2025-01-01 10:00:00", "2025-01-01 10:01:00", "2025-01-01 10:02:00"],
        [10.0, 20.0, 30.0],
    )
    assert detect_streaks(df, threshold=70.0) == []


def test_all_above_threshold_single_streak():
    df = _make_df(
        ["2025-01-01 10:00:00", "2025-01-01 10:01:00", "2025-01-01 10:02:00"],
        [75.0, 80.0, 85.0],
    )
    streaks = detect_streaks(df, threshold=70.0)
    assert len(streaks) == 1
    assert streaks[0].duration_seconds == pytest.approx(120.0)
    assert streaks[0].peak_cpu == 85.0
    assert streaks[0].avg_cpu == pytest.approx(80.0)


def test_two_separate_streaks():
    df = _make_df(
        [
            "2025-01-01 10:00:00",  # above
            "2025-01-01 10:01:00",  # above
            "2025-01-01 10:02:00",  # below — breaks streak
            "2025-01-01 10:03:00",  # above — new streak
            "2025-01-01 10:04:00",  # above
        ],
        [80.0, 85.0, 20.0, 75.0, 90.0],
    )
    streaks = detect_streaks(df, threshold=70.0)
    assert len(streaks) == 2
    assert streaks[0].duration_seconds == pytest.approx(60.0)
    assert streaks[1].duration_seconds == pytest.approx(60.0)


def test_gap_breaks_streak():
    """Two above-threshold samples separated by > max_gap should be two streaks."""
    df = _make_df(
        [
            "2025-01-01 10:00:00",
            "2025-01-01 10:10:00",  # 600 s gap — > default 120 s
        ],
        [80.0, 85.0],
    )
    streaks = detect_streaks(df, threshold=70.0, max_gap_seconds=120.0)
    assert len(streaks) == 2


def test_gap_within_tolerance_continues_streak():
    df = _make_df(
        [
            "2025-01-01 10:00:00",
            "2025-01-01 10:01:00",  # 60 s — within 120 s tolerance
        ],
        [80.0, 85.0],
    )
    streaks = detect_streaks(df, threshold=70.0, max_gap_seconds=120.0)
    assert len(streaks) == 1


def test_exact_threshold_counts_as_streak():
    df = _make_df(["2025-01-01 10:00:00"], [70.0])
    streaks = detect_streaks(df, threshold=70.0)
    assert len(streaks) == 1


def test_streaks_to_dataframe_empty():
    df = streaks_to_dataframe([])
    assert df.empty
    assert set(df.columns) == {
        "start_time", "end_time", "duration_seconds",
        "avg_cpu", "peak_cpu", "sample_count"
    }


def test_streaks_to_dataframe_populated():
    df = _make_df(
        ["2025-01-01 10:00:00", "2025-01-01 10:01:00"],
        [80.0, 90.0],
    )
    streaks = detect_streaks(df, threshold=70.0)
    result = streaks_to_dataframe(streaks)
    assert len(result) == 1
    assert "peak_cpu" in result.columns