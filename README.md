# 🌱 EcoStreak

![CI](https://github.com/Arundhat1/Ecostreak-Project/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**EcoStreak** is a Python CLI tool.It continously monitors per-process CPU usage. It then detects sustained high-load sessions or streaks and translates them into estimated enery consumption unit. So it becomes evident which applications are draining the battery and why.

> *"Yesterday, Chrome caused 83% of all high-load streaks on my machine. VS Code caused 17%. EcoStreak told me that in 10 seconds."*

---

## Why EcoStreak?

Most system monitors show you CPU% right now. That's not useful.

What's useful is:
- **Which app** caused sustained high load?
- **How long** did it run above threshold?
- **How much energy** did that cost?

EcoStreak answers all three.

---

## How It Works

```
psutil samples CPU every N seconds
          │
          ▼
Per-process data written to CSV
          │
          ▼
Single-pass O(n) streak detection
(contiguous samples ≥ threshold = one streak)
          │
          ▼
Gap-aware energy estimation
(cpu% × TDP × Δt, gaps skipped)
          │
          ▼
Process attribution
(which app ran during each streak?)
          │
          ▼
Dashboard PNG + CLI report
```

---

## Project Structure

```
EcoStreak-Project/
├── ecostreak/
│   ├── core/
│   │   ├── logger.py      # psutil-based per-process sampler
│   │   ├── streak.py      # O(n) streak detection algorithm
│   │   ├── energy.py      # gap-aware TDP energy estimator
│   │   ├── analyzer.py    # summary stats + process attribution
│   │   └── visualize.py   # matplotlib dashboard (saves to disk)
│   └── cli/
│       └── main.py        # argparse CLI entry point
├── tests/
│   ├── test_streak.py     # 9 edge-case tests for streak detection
│   └── test_energy.py     # 5 tests for energy estimation
├── data/
│   └── sample/
│       └── cpu_log_sample.csv   # real sample log for demo
├── .github/workflows/
│   └── ci.yml             # GitHub Actions: pytest on Python 3.9 + 3.11
└── pyproject.toml
```

---

## Installation

```bash
git clone https://github.com/Arundhat1/Ecostreak-Project.git
cd Ecostreak-Project

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -e .
```

---

## Quick Start

**Try it immediately with the sample log (no waiting):**

```bash
python -m ecostreak.cli.main --skip-logging \
  --log-path data/sample/cpu_log_sample.csv \
  --threshold 50
```

**Run a live 5-minute session (stress your CPU to see streaks):**

```bash
python -m ecostreak.cli.main --duration 300 --interval 2 --threshold 50
```

**Full 30-minute monitoring session:**

```bash
python -m ecostreak.cli.main --duration 1800 --interval 5 --threshold 70
```

---

## Sample Output

```
────────────────────────────────────────────────────
  EcoStreak Report
────────────────────────────────────────────────────
  Samples         : 335
  Active time     : 0.50 h
  CPU (avg/peak)  : 12.0% / 97.8%
  Energy          : 0.4589 Wh
  Streaks (≥50%)  : 4
  Longest streak  : 42.0 s
  % time in streak: 3.3%
────────────────────────────────────────────────────

  Top 5 streaks:
    1. 2026-07-20T16:36:40  →  2026-07-20T16:37:02  (42 s, peak 97.8%)
    2. 2026-07-20T16:38:10  →  2026-07-20T16:38:24  (14 s, peak 77.8%)

  Top processes during streaks (≥50%):
  Process                  Avg CPU    Peak  Appearances   Share
  ----------------------- -------- ------- ------------ -------
  chrome.exe                 73.0%   97.8%            5   83.3%
  Code.exe                   62.1%   62.1%            1   16.7%
```

---

## CLI Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--duration` | `60` | Logging duration in seconds |
| `--interval` | `2.0` | Sampling interval in seconds |
| `--threshold` | `70.0` | High-CPU threshold in percent |
| `--tdp` | `45.0` | CPU thermal design power (watts) |
| `--top-n` | `10` | Processes to record per sample |
| `--top-procs` | `5` | Processes to show in attribution |
| `--output-dir` | `data/raw` | Where to save CSV logs |
| `--figures-dir` | `outputs/figures` | Where to save dashboard PNG |
| `--skip-logging` | — | Analyse existing log, skip collection |
| `--log-path` | — | Path to existing log (use with above) |
| `--no-plot` | — | Skip dashboard generation |
| `--json` | — | Print results as JSON |

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

18 tests covering:
- Streak detection edge cases (empty data, single row, gaps, exact threshold)
- Energy estimation (gap skipping, per-row delta, invalid values)

---

## Design Decisions

**Why CSV instead of SQLite?**
CSV requires zero setup. It is human readable and it is enough for single machine monitoring at 5 second intervals. If session is of 30 minutes then approx 3,600 rows gets genrated which is wwithin CSV's practical limits. If I had to perform query across sessions or if I had to support concurrent writed SQLite would have been my choice.

**Why O(n) streak detection?**
A naive sliding-window approach is O(n^2). If session is of 24 hours with rate of 1 sample/second then 86,400 rows gets generated which means 7.5 billion comparisons. Ecostreak visits each row exactly once, streaks are opened and closed in O(1). It also handles variable sampling intervals naturally

**Why gap-aware energy estimation?**
A fixed-interval assumption inflates energy estimates when the machine sleeps or the logger restarts. EcoStreak computes per-row time deltas using `timestamp.diff()` and skips gaps wider than 5 minutes. This was caught from real data — one session had a 96-minute gap that would have multiplied estimated energy by 10×.

**Why psutil warm-up?**
`psutil.cpu_percent(interval=None)` ALWAYS returns 0.0 on the first call per process . Ecostreak calls it once while initialising internal counter then it sleeps one full interval and then begins sampling otherwise every first reading will be invalid.

---

## Limitations

- Energy estimate is based on CPU TDP (manufacturer ceiling), not actual socket power draw. Real consumption varies with frequency scaling and core count.
- Process attribution works best with per-process logs. System-wide logs show total CPU only.
- Designed for single-machine use. Multi-server monitoring would require a push-based architecture (Prometheus + TimescaleDB).

---

## Future Work

- [ ] Intel RAPL integration for real power measurement (Linux)
- [ ] CO₂ equivalence using regional grid carbon intensity
- [ ] Streamlit dashboard for live monitoring
- [ ] Multi-day log stitching and weekly reports
- [ ] Docker support

---

## Author

**Arundhati Datta Hangargekar**