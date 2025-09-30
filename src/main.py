# main.py
import os
from logger import log_cpu_usage
from energy import estimate_energy
from visualize import plot_usage


def main():
    log_path = os.path.join("data", "cpu_log.csv")

    print("🔹 Logging CPU usage for 30 minutes...")
    log_cpu_usage( duration=60*30, interval=5, save_dir ='data')

    print("\n📊 Estimating energy consumption...")
    energy_stats = estimate_energy(log_path=log_path, tdp_watts=45)
    for k, v in energy_stats.items():
        print(f"{k}: {v}")

    print("\n📈 Visualizing CPU usage...")
    plot_usage(log_path=log_path)


if __name__ == "__main__":
    main()
