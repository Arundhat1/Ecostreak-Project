# tests/test_energy.py
"""
Unit tests for energy estimation.
Tests write a temp CSV, call estimate_energy, then clean up.
"""

import os
import tempfile

import pandas as pd
import pytest

from ecostreak.core.energy import estimate_energy, load_log


def _write_csv(rows: list[dict]) -> str:
    """Write rows to a temp CSV and return the path."""
    df = pd.DataFrame(rows)
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    )
    df.to_csv(tmp.name, index=False)
    tmp.close()
    return tmp.name


# ---------------------------------------------------------------------------

def test_estimate_energy_normal():
    path = _write_csv([
        {"timestamp": "2025-01-01T10:00:00", "cpu_percent": 50.0},
        {"timestamp": "2025-01-01T10:01:00", "cpu_percent": 50.0},  # 60 s
    ])
    try:
        result = estimate_energy(path, tdp_watts=100.0)
        # power = 0.5 * 100 = 50 W over 60 s = 3000 J
        assert result["estimated_energy_joules"] == pytest.approx(3000.0, rel=1e-3)
    finally:
        os.unlink(path)


def test_estimate_energy_skips_large_gaps():
    path = _write_csv([
        {"timestamp": "2025-01-01T10:00:00", "cpu_percent": 80.0},
        {"timestamp": "2025-01-01T11:00:00", "cpu_percent": 80.0},  # 3600 s gap — skipped
    ])
    try:
        result = estimate_energy(path, tdp_watts=45.0, max_gap_seconds=300.0)
        # Gap is skipped → energy should be 0
        assert result["estimated_energy_joules"] == pytest.approx(0.0)
        assert result["skipped_gap_seconds"] == pytest.approx(3600.0)
    finally:
        os.unlink(path)


def test_estimate_energy_single_row():
    path = _write_csv([
        {"timestamp": "2025-01-01T10:00:00", "cpu_percent": 60.0},
    ])
    try:
        result = estimate_energy(path)
        assert result["estimated_energy_joules"] == 0.0
        assert result["data_points"] == 1
    finally:
        os.unlink(path)


def test_load_log_invalid_cpu_values_dropped():
    path = _write_csv([
        {"timestamp": "2025-01-01T10:00:00", "cpu_percent": -5.0},   # invalid
        {"timestamp": "2025-01-01T10:01:00", "cpu_percent": 50.0},   # valid
        {"timestamp": "2025-01-01T10:02:00", "cpu_percent": 150.0},  # invalid
    ])
    try:
        df = load_log(path)
        assert len(df) == 1
        assert df["cpu_percent"].iloc[0] == 50.0
    finally:
        os.unlink(path)


def test_load_log_empty_raises():
    path = _write_csv([])
    try:
        with pytest.raises(ValueError, match="empty"):
            load_log(path)
    finally:
        os.unlink(path)