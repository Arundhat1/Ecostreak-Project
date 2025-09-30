# analyzer.py
import pandas as pd

def analyze_usage(log_path="data/cpu_log.csv", threshold=50):
    """
    Analyzes CPU log and returns:
    - average CPU usage
    - peak CPU usage
    - % of time above threshold
    """
    df = pd.read_csv(log_path)

    avg_usage = df["cpu_percent"].mean()
    peak_usage = df["cpu_percent"].max()
    above_threshold = (df["cpu_percent"] >= threshold).mean() * 100

    summary = {
        "average_cpu": round(avg_usage, 2),
        "peak_cpu": peak_usage,
        "percent_time_above_threshold": round(above_threshold, 2)
    }
    return summary

if __name__ == "__main__":
    print(analyze_usage())
