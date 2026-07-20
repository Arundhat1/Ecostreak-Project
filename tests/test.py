from ecostreak.core.visualize import plot_usage

plot_usage(
    log_path="C:/Users/ARUNDHATI/Downloads/EcoStreak-Project/data/cpu_log_2026-04-13_223019.csv",  
    tdp_watts=45,                    # or whatever you used
    threshold=50,
    output_dir="outputs"
)