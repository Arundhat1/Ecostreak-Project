# core/main.py
"""
EcoStreak entry point.

Usage examples
--------------
# Quick demo (60 seconds, stress your CPU to see streaks):
    python -m ecostreak.cli.main --duration 60 --interval 2 --threshold 50

# Full session (30 minutes):
    python -m ecostreak.cli.main --duration 1800 --interval 5 --threshold 70

# Analyse existing log, skip collection:
    python -m ecostreak.cli.main --skip-logging --log-path data/raw/cpu_log_sample.csv

# JSON output for scripting:
    python -m ecostreak.cli.main --skip-logging --log-path data/raw/cpu_log_sample.csv --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ecostreak",
        description="EcoStreak — CPU usage streak tracker with energy mapping",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    log_group = parser.add_argument_group("Logging")
    log_group.add_argument("--duration", type=float, default=60.0,
                           help="Total logging duration in seconds")
    log_group.add_argument("--interval", type=float, default=2.0,
                           help="Sampling interval in seconds")
    log_group.add_argument("--top-n", type=int, default=10,
                           help="Top N processes to record per sample")
    log_group.add_argument("--output-dir", type=str, default="data/raw",
                           help="Directory for log CSV files")
    log_group.add_argument("--skip-logging", action="store_true",
                           help="Skip data collection; analyse --log-path directly")
    log_group.add_argument("--log-path", type=str, default=None,
                           help="Existing log file to analyse (requires --skip-logging)")

    analysis_group = parser.add_argument_group("Analysis")
    analysis_group.add_argument("--tdp", type=float, default=45.0,
                                help="CPU thermal design power in watts")
    analysis_group.add_argument("--threshold", type=float, default=70.0,
                                help="High-CPU threshold in percent")
    analysis_group.add_argument("--top-procs", type=int, default=5,
                                help="Top N processes to show in attribution report")

    out_group = parser.add_argument_group("Output")
    out_group.add_argument("--figures-dir", type=str, default="outputs/figures",
                           help="Directory for dashboard PNG")
    out_group.add_argument("--no-plot", action="store_true",
                           help="Skip generating the dashboard plot")
    out_group.add_argument("--json", action="store_true",
                           help="Print analysis results as JSON to stdout")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main entry point. Returns 0 on success, 1 on error."""
    args = _parse_args(argv)

    # Deferred imports — --help returns instantly without loading heavy deps
    from ecostreak.core.logger import log_cpu_usage
    from ecostreak.core.energy import estimate_energy
    from ecostreak.core.analyzer import analyze_usage, top_processes_during_streaks
    from ecostreak.core.streak import detect_streaks
    from ecostreak.core.energy import load_log
    from ecostreak.core.visualize import plot_usage

    log_path: str | None = None

    # ------------------------------------------------------------------
    # Step 1: Logging
    # ------------------------------------------------------------------
    if args.skip_logging:
        if not args.log_path:
            print("❌ --skip-logging requires --log-path", file=sys.stderr)
            return 1
        if not os.path.isfile(args.log_path):
            print(f"❌ Log file not found: {args.log_path}", file=sys.stderr)
            return 1
        log_path = args.log_path
        print(f"⏭️  Skipping logging — using: {log_path}")
    else:
        print(
            f"🔹 Logging CPU usage for {args.duration:.0f} s "
            f"(interval={args.interval} s, top-{args.top_n} processes)…"
        )
        log_path = log_cpu_usage(
            interval=args.interval,
            duration=args.duration,
            top_n=args.top_n,
            save_dir=args.output_dir,
        )

    # ------------------------------------------------------------------
    # Step 2: Energy estimation
    # ------------------------------------------------------------------
    print("\n⚡ Estimating energy consumption…")
    try:
        energy = estimate_energy(log_path, tdp_watts=args.tdp)
    except Exception as exc:
        print(f"❌ Energy estimation failed: {exc}", file=sys.stderr)
        return 1

    # ------------------------------------------------------------------
    # Step 3: Streak + usage analysis
    # ------------------------------------------------------------------
    print("📊 Analysing CPU streaks…")
    try:
        analysis = analyze_usage(log_path, threshold=args.threshold)
    except Exception as exc:
        print(f"❌ Analysis failed: {exc}", file=sys.stderr)
        return 1

    # ------------------------------------------------------------------
    # Step 4: Process attribution
    # ------------------------------------------------------------------
    streaks = detect_streaks(load_log(log_path), threshold=args.threshold)
    try:
        proc_df = top_processes_during_streaks(log_path, streaks, top_n=args.top_procs)
    except Exception:
        proc_df = None  # attribution is best-effort; don't fail the run

    # ------------------------------------------------------------------
    # Step 5: Output
    # ------------------------------------------------------------------
    if args.json:
        combined = {**energy, **analysis}
        if proc_df is not None and not proc_df.empty:
            combined["top_processes"] = proc_df.to_dict(orient="records")
        print(json.dumps(combined, indent=2, default=str))
    else:
        print(
            f"\n{'─' * 52}\n"
            f"  EcoStreak Report\n"
            f"{'─' * 52}\n"
            f"  Samples         : {analysis['data_points']}\n"
            f"  Active time     : {energy['active_seconds'] / 3600:.2f} h\n"
            f"  CPU (avg/peak)  : {energy['avg_cpu_percent']:.1f}% / {energy['max_cpu_percent']:.1f}%\n"
            f"  Energy          : {energy['estimated_energy_wh']:.4f} Wh\n"
            f"  Streaks (≥{args.threshold:.0f}%) : {analysis['streak_count']}\n"
            f"  Longest streak  : {analysis['longest_streak_seconds']:.1f} s\n"
            f"  % time in streak: {analysis['pct_time_above_threshold']:.1f}%\n"
            f"{'─' * 52}"
        )

        if analysis["streaks"]:
            print("\n  Top 5 streaks:")
            for i, s in enumerate(analysis["streaks"][:5], 1):
                print(
                    f"    {i}. {s['start_time']}  →  {s['end_time']}"
                    f"  ({s['duration_seconds']:.0f} s, peak {s['peak_cpu']:.1f}%)"
                )

        # Process attribution block — the "which app wasted energy" answer
        if proc_df is not None and not proc_df.empty:
            print(f"\n  Top processes during streaks (≥{args.threshold:.0f}%):")
            print(f"  {'Process':<22} {'Avg CPU':>8} {'Peak':>7} {'Appearances':>12} {'Share':>7}")
            print(f"  {'─'*22} {'─'*8} {'─'*7} {'─'*12} {'─'*7}")
            for _, row in proc_df.iterrows():
                print(
                    f"  {str(row['process_name']):<22} "
                    f"{row['avg_cpu_during_streak']:>7.1f}% "
                    f"{row['peak_cpu']:>6.1f}% "
                    f"{int(row['appearances']):>12} "
                    f"{row['streak_share_pct']:>6.1f}%"
                )
        elif analysis["streak_count"] > 0:
            print("\n  ℹ️  Process attribution unavailable (log has no process_name column)")

    # ------------------------------------------------------------------
    # Step 6: Plot
    # ------------------------------------------------------------------
    if not args.no_plot:
        print("\n📈 Generating dashboard…")
        try:
            plot_path = plot_usage(
                log_path=log_path,
                tdp_watts=args.tdp,
                threshold=args.threshold,
                output_dir=args.figures_dir,
            )
            print(f"✅ Plot saved: {plot_path}")
        except Exception as exc:
            print(f"⚠️  Plot generation failed: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())