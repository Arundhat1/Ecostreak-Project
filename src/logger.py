#logger.py
import psutil
import time
import csv
import os
from datetime import datetime

def log_cpu_usage(interval=5, duration=60, top_n=10, save_dir="data"):
    """
    Logs CPU usage per process to a new CSV file per session.

    - interval: seconds between samples
    - duration: total logging time in seconds
    - top_n: only log top N CPU-consuming processes
    - save_dir: directory to store CSV files
    """
    os.makedirs(save_dir, exist_ok=True)

    # Generate a new CSV filename for this session
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_file = os.path.join(save_dir, f"cpu_log_{timestamp_str}.csv")

    with open(log_file, "w", newline="") as f:
        writer = csv.writer(f)
        # CSV header
        writer.writerow(["timestamp", "pid", "process_name", "cpu_percent"])

        start = time.time()
        while time.time() - start < duration:
            timestamp = datetime.now().isoformat()
            
            # Get all processes and their CPU %
            processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    cpu = proc.cpu_percent(interval=None)  # non-blocking
                    processes.append((proc.info['pid'], proc.info['name'], cpu))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU %, descending, take top N
            processes.sort(key=lambda x: x[2], reverse=True)
            for pid, name, cpu in processes[:top_n]:
                writer.writerow([timestamp, pid, name, cpu])
            
            # Wait for next interval
            time.sleep(interval)

    print(f"✅ CPU usage logged to {log_file}")
