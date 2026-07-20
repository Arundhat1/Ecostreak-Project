# core/visualize.py
"""
CPU usage visualisation.

All plot functions write to disk and return the output file path.
No plt.show() calls — safe for headless / server environments.
"""

from __future__ import annotations

import os

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import seaborn as sns

from ecostreak.core.energy import estimate_energy, load_log
from ecostreak.core.streak import detect_streaks, streaks_to_dataframe

plt.style.use("seaborn-v0_8")
sns.set_palette("husl")


def plot_usage(
    log_path: str = "data/cpu_log.csv",
    tdp_watts: float = 45.0,
    threshold: float = 70.0,
    output_dir: str = "data",
    filename: str | None = None,
) -> str:
    """
    Generate and save the main CPU usage dashboard.

    Layout
    ------
    Row 0 (full width): time-series with streak highlights + threshold lines
    Row 1 left:         usage distribution histogram
    Row 1 centre:       cumulative energy (Wh) over time
    Row 1 right:        usage category pie chart
    Row 2 (full width): summary statistics text box

    Parameters
    ----------
    log_path : str
        Path to CPU log CSV.
    tdp_watts : float
        CPU thermal design power in watts.
    threshold : float
        High-CPU threshold used for streak shading.
    output_dir : str
        Directory where the PNG will be saved.
    filename : str | None
        Override output filename.  Defaults to cpu_dashboard_<timestamp>.png.

    Returns
    -------
    str
        Absolute path to the saved PNG file.
    """
    df = load_log(log_path)
    energy_stats = estimate_energy(log_path, tdp_watts=tdp_watts)
    streaks = detect_streaks(df, threshold=threshold)

    os.makedirs(output_dir, exist_ok=True)
    if filename is None:
        ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cpu_dashboard_{ts}.png"
    output_path = os.path.join(output_dir, filename)

    fig = plt.figure(figsize=(16, 12))

    # ------------------------------------------------------------------
    # Row 0: Time-series
    # ------------------------------------------------------------------
    ax1 = plt.subplot2grid((3, 3), (0, 0), colspan=3)

    ax1.plot(
        df["timestamp"], df["cpu_percent"],
        linewidth=1.8, alpha=0.85, color="#2E86C1", label="CPU %",
    )
    ax1.fill_between(df["timestamp"], df["cpu_percent"], alpha=0.25, color="#2E86C1")

    # Shade streak regions
    for streak in streaks:
        ax1.axvspan(streak.start_time, streak.end_time, alpha=0.15, color="#E74C3C",
                    label="_nolegend_")

    ax1.axhline(threshold, color="#E74C3C", linestyle="--", linewidth=1.8, alpha=0.8,
                label=f"Threshold ({threshold:.0f}%)")
    ax1.axhline(90, color="#922B21", linestyle="--", linewidth=1.8, alpha=0.8,
                label="Critical (90%)")
    ax1.axhline(
        df["cpu_percent"].mean(),
        color="#F39C12", linestyle="-.", linewidth=1.8, alpha=0.9,
        label=f"Mean ({energy_stats['avg_cpu_percent']:.1f}%)",
    )

    ax1.set_title("CPU Usage Over Time  (red bands = streaks)", fontsize=15, fontweight="bold", pad=14)
    ax1.set_xlabel("Time", fontsize=11)
    ax1.set_ylabel("CPU %", fontsize=11)
    ax1.set_ylim(0, 105)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax1.legend(loc="upper right", framealpha=0.9, fontsize=9)
    ax1.grid(True, alpha=0.3)

    # ------------------------------------------------------------------
    # Row 1 left: Distribution histogram
    # ------------------------------------------------------------------
    ax2 = plt.subplot2grid((3, 3), (1, 0))
    ax2.hist(df["cpu_percent"], bins=20, alpha=0.75, color="#8E44AD", edgecolor="black")
    ax2.axvline(df["cpu_percent"].mean(), color="#F39C12", linestyle="--", linewidth=2,
                label="Mean")
    ax2.axvline(threshold, color="#E74C3C", linestyle="--", linewidth=2,
                label=f"Threshold ({threshold:.0f}%)")
    ax2.set_title("Usage Distribution", fontsize=11, fontweight="bold")
    ax2.set_xlabel("CPU %")
    ax2.set_ylabel("Samples")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # ------------------------------------------------------------------
    # Row 1 centre: Cumulative energy
    # ------------------------------------------------------------------
    ax3 = plt.subplot2grid((3, 3), (1, 1))

    deltas = df["timestamp"].diff().dt.total_seconds().fillna(0)
    df_e = df.copy()
    df_e["delta_s"] = deltas.clip(upper=300)  # cap gaps at 5 min
    df_e["energy_wh"] = (df_e["cpu_percent"] / 100.0) * tdp_watts * (df_e["delta_s"] / 3600.0)
    df_e["cumulative_wh"] = df_e["energy_wh"].cumsum()

    ax3.plot(df["timestamp"], df_e["cumulative_wh"], color="#27AE60", linewidth=2)
    ax3.set_title("Cumulative Energy (Wh)", fontsize=11, fontweight="bold")
    ax3.set_xlabel("Time")
    ax3.set_ylabel("Wh")
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax3.grid(True, alpha=0.3)

    # ------------------------------------------------------------------
    # Row 1 right: Usage category pie
    # ------------------------------------------------------------------
    ax4 = plt.subplot2grid((3, 3), (1, 2))
    low = int((df["cpu_percent"] < 30).sum())
    medium = int(((df["cpu_percent"] >= 30) & (df["cpu_percent"] < threshold)).sum())
    high = int((df["cpu_percent"] >= threshold).sum())
    labels = [f"Low (<30%)", f"Medium (30–{threshold:.0f}%)", f"High (≥{threshold:.0f}%)"]
    sizes = [low, medium, high]
    colors = ["#2ECC71", "#F39C12", "#E74C3C"]
    non_zero = [(l, s, c) for l, s, c in zip(labels, sizes, colors) if s > 0]
    if non_zero:
        nz_labels, nz_sizes, nz_colors = zip(*non_zero)
        ax4.pie(nz_sizes, labels=nz_labels, colors=nz_colors, autopct="%1.1f%%", startangle=90)
    ax4.set_title("Usage Categories", fontsize=11, fontweight="bold")

    # ------------------------------------------------------------------
    # Row 2: Summary statistics
    # ------------------------------------------------------------------
    ax5 = plt.subplot2grid((3, 3), (2, 0), colspan=3)
    ax5.axis("off")

    total_streak_s = sum(s.duration_seconds for s in streaks)
    pct_streak = (total_streak_s / energy_stats["active_seconds"] * 100) if energy_stats["active_seconds"] > 0 else 0.0
    summary = (
        f"SYSTEM PERFORMANCE SUMMARY\n\n"
        f"Monitoring: {energy_stats['active_seconds'] / 3600:.2f} h active  |  "
        f"{energy_stats['data_points']} samples  |  "
        f"{energy_stats['skipped_gap_seconds']:.0f} s gap-skipped\n"
        f"CPU — min: {energy_stats['min_cpu_percent']:.1f}%  "
        f"avg: {energy_stats['avg_cpu_percent']:.1f}%  "
        f"max: {energy_stats['max_cpu_percent']:.1f}%\n"
        f"Energy — {energy_stats['estimated_energy_wh']:.4f} Wh  "
        f"({energy_stats['estimated_energy_joules']:.1f} J)  |  "
        f"TDP: {tdp_watts} W\n"
        f"Streaks — {len(streaks)} detected  |  "
        f"{total_streak_s:.0f} s total streak time  |  "
        f"{pct_streak:.1f}% of active time above {threshold:.0f}%"
    )
    ax5.text(
        0.03, 0.92, summary,
        transform=ax5.transAxes, fontsize=10.5,
        verticalalignment="top", family="monospace",
        bbox=dict(boxstyle="round,pad=0.6", facecolor="#ECF0F1", alpha=0.9),
    )

    plt.tight_layout(pad=2.5)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"📊 Dashboard saved to {output_path}")
    return output_path