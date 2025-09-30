# 🌱 EcoStreak

EcoStreak is a lightweight awareness project that tracks **CPU usage streaks** to make energy consumption more visible and intuitive.  
The idea is simple: by monitoring continuous CPU usage above a certain threshold, we can highlight "wasteful streaks" and translate them into real-world equivalents like **kWh, CO₂ emissions, or time wasted**.

---
<img width="1520" height="786" alt="Figure_1" src="https://github.com/user-attachments/assets/ca6b87ab-1d1a-402d-acb1-bd055d1a9bc7" />

## 📌 Phase 1 (Current Progress)

- ✅ System-level CPU monitoring using `psutil` (Python)
- ✅ Continuous logging of CPU usage
- ✅ Data stored in **CSV files**, separated by process name
- ✅ Task Scheduler set up for long-term data collection (Windows)
- ✅ First commit pushed to GitHub

---

## ⚙️ Features in Progress
- Identify **background vs. user-intended processes**
- Estimate energy usage (CPU time × TDP model, initial approximation)
- Define a **"streak"** (continuous usage above a threshold, e.g., >70% CPU for X seconds)
- Data visualization ideas:
  - Daily digest
  - Graphs of streaks
  - Real-world equivalents (e.g., “This streak = powering a bulb for 2 hrs”)

---

## 🚀 How to Run (Phase 1)
1. Clone the repo:
   ```bash
   git clone https://github.com/<your-username>/EcoStreak.git
   cd EcoStreak
