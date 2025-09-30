# energy.py
import pandas as pd

def estimate_energy(log_path="data/cpu_log.csv", tdp_watts=45):
    """
    Estimates CPU energy consumed based on usage.
    Energy = CPU% × TDP × time
    """
    try:
        df = pd.read_csv(
            log_path,
            usecols=["timestamp", "cpu_percent"],  # read only expected cols
            on_bad_lines="skip"  # skip malformed rows
        )
    except Exception as e:
        return {"error": f"Failed to read log file: {e}"}

    if df.empty:
        return {"error": "Log file is empty or invalid."}

    # Detect interval dynamically
    if len(df) > 1:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        interval = (df["timestamp"].iloc[1] - df["timestamp"].iloc[0]).total_seconds()
    else:
        interval = 60  # fallback (default 1 min)

    total_seconds = len(df) * interval
    avg_usage = df["cpu_percent"].mean() / 100.0
    energy_joules = avg_usage * tdp_watts * total_seconds

    return {
        "avg_cpu_percent": round(avg_usage * 100, 2),
        "estimated_energy_joules": round(energy_joules, 2),
        "estimated_energy_wh": round(energy_joules / 3600, 4),  # watt-hours
        "interval_seconds": interval,
        "data_points": len(df)
    }

if __name__ == "__main__":
    print(estimate_energy())
