#visualise.py
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import seaborn as sns

# Set style for better looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

def estimate_energy(df, tdp_watts=45, interval_seconds=60):
    """
    Estimates CPU energy consumed based on usage.
    """
    if df.empty:
        return {}
    
    total_seconds = len(df) * interval_seconds
    avg_usage = df["cpu_percent"].mean() / 100.0
    energy_joules = avg_usage * tdp_watts * total_seconds
    
    return {
        "avg_cpu_percent": round(avg_usage, 2),
        "estimated_energy_joules": round(energy_joules, 2),
        "estimated_energy_wh": round(energy_joules / 3600, 4),
        "max_cpu_percent": df["cpu_percent"].max(),
        "min_cpu_percent": df["cpu_percent"].min(),
        "total_hours": round(total_seconds / 3600, 2)
    }

def plot_usage(log_path="data/cpu_log.csv", tdp_watts=45):
    """
    Creates an enhanced, more intuitive CPU usage visualization with energy estimates.
    """
    try:
        # Read and process data
        df = pd.read_csv(log_path, on_bad_lines="skip")
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Detect sampling interval
        if len(df) > 1:
            interval = (df["timestamp"].iloc[1] - df["timestamp"].iloc[0]).total_seconds()
        else:
            interval = 60
            
        # Calculate energy metrics
        energy_stats = estimate_energy(df, tdp_watts, interval)
        
        # Create figure with subplots
        fig = plt.figure(figsize=(16, 12))
        
        # Main time series plot (top, larger)
        ax1 = plt.subplot2grid((3, 3), (0, 0), colspan=3, rowspan=1)
        
        # Plot CPU usage line
        ax1.plot(df["timestamp"], df["cpu_percent"], 
                linewidth=2, alpha=0.8, color='#2E86C1', label='CPU Usage')
        
        # Fill area under curve for visual impact
        ax1.fill_between(df["timestamp"], df["cpu_percent"], alpha=0.3, color='#2E86C1')
        
        # Add threshold lines with different colors
        ax1.axhline(70, color="#E74C3C", linestyle="--", alpha=0.7, linewidth=2, label="High Usage (70%)")
        ax1.axhline(90, color="#C0392B", linestyle="--", alpha=0.7, linewidth=2, label="Critical (90%)")
        ax1.axhline(df["cpu_percent"].mean(), color="#F39C12", linestyle="-.", alpha=0.8, 
                   linewidth=2, label=f"Average ({energy_stats['avg_cpu_percent']:.1f}%)")
        
        ax1.set_title("CPU Usage Over Time", fontsize=16, fontweight='bold', pad=20)
        ax1.set_xlabel("Time", fontsize=12)
        ax1.set_ylabel("CPU Usage (%)", fontsize=12)
        ax1.legend(loc='upper right', framealpha=0.9)
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 100)
        
        # Usage distribution histogram
        ax2 = plt.subplot2grid((3, 3), (1, 0), colspan=1)
        ax2.hist(df["cpu_percent"], bins=20, alpha=0.7, color='#8E44AD', edgecolor='black')
        ax2.axvline(df["cpu_percent"].mean(), color="#F39C12", linestyle="--", linewidth=2)
        ax2.set_title("Usage Distribution", fontsize=12, fontweight='bold')
        ax2.set_xlabel("CPU %")
        ax2.set_ylabel("Frequency")
        ax2.grid(True, alpha=0.3)
        
        # Energy consumption over time
        ax3 = plt.subplot2grid((3, 3), (1, 1), colspan=1)
        
        # Calculate cumulative energy consumption
        df_energy = df.copy()
        df_energy['energy_wh'] = (df_energy['cpu_percent'] / 100) * tdp_watts * (interval / 3600)
        df_energy['cumulative_energy'] = df_energy['energy_wh'].cumsum()
        
        ax3.plot(df["timestamp"], df_energy['cumulative_energy'], 
                color='#27AE60', linewidth=2, marker='o', markersize=2)
        ax3.set_title("Cumulative Energy", fontsize=12, fontweight='bold')
        ax3.set_xlabel("Time")
        ax3.set_ylabel("Energy (Wh)")
        ax3.grid(True, alpha=0.3)
        
        # Usage categories pie chart
        ax4 = plt.subplot2grid((3, 3), (1, 2), colspan=1)
        
        # Categorize usage
        low_usage = (df["cpu_percent"] < 30).sum()
        medium_usage = ((df["cpu_percent"] >= 30) & (df["cpu_percent"] < 70)).sum()
        high_usage = (df["cpu_percent"] >= 70).sum()
        
        categories = ['Low (<30%)', 'Medium (30-70%)', 'High (≥70%)']
        sizes = [low_usage, medium_usage, high_usage]
        colors = ['#2ECC71', '#F39C12', '#E74C3C']
        
        ax4.pie(sizes, labels=categories, colors=colors, autopct='%1.1f%%', startangle=90)
        ax4.set_title("Usage Categories", fontsize=12, fontweight='bold')
        
        # Statistics summary (bottom row)
        ax5 = plt.subplot2grid((3, 3), (2, 0), colspan=3)
        ax5.axis('off')
        
        # Create summary statistics
        stats_text = f"""
        📊 SYSTEM PERFORMANCE SUMMARY
        
        ⏱️  Monitoring Period: {energy_stats['total_hours']} hours ({len(df)} data points)
        📈 CPU Usage: Min: {energy_stats['min_cpu_percent']:.1f}% | Avg: {energy_stats['avg_cpu_percent']:.1f}% | Max: {energy_stats['max_cpu_percent']:.1f}%
        ⚡ Energy Consumption: {energy_stats['estimated_energy_wh']:.3f} Wh ({energy_stats['estimated_energy_joules']:.0f} Joules)
        🔧 CPU TDP: {tdp_watts}W | Sampling Interval: {interval:.0f}s
        
        💡 Performance Insights:
        • {(high_usage/len(df)*100):.1f}% of time spent in high usage (≥70%)
        • Estimated daily energy cost: ~{(energy_stats['estimated_energy_wh'] * 24 / energy_stats['total_hours'] * 0.12):.3f} USD (at 12¢/kWh)
        • Peak usage periods: {'Frequent' if high_usage > len(df) * 0.2 else 'Occasional'}
        """
        
        ax5.text(0.05, 0.95, stats_text, transform=ax5.transAxes, fontsize=11,
                verticalalignment='top', bbox=dict(boxstyle="round,pad=0.5", 
                facecolor='lightgray', alpha=0.8))
        
        plt.tight_layout(pad=3.0)
        plt.show()
        
        return energy_stats
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find log file at '{log_path}'")
        return None
    except Exception as e:
        print(f"❌ Error processing data: {e}")
        return None

def create_sample_data(filename="data/cpu_log.csv", hours=24):
    """
    Creates sample CPU usage data for demonstration.
    """
    import os
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Generate realistic CPU usage patterns
    np.random.seed(42)
    timestamps = []
    cpu_usage = []
    
    start_time = datetime.now() - timedelta(hours=hours)
    
    for i in range(hours * 60):  # One data point per minute
        current_time = start_time + timedelta(minutes=i)
        timestamps.append(current_time)
        
        # Create realistic usage patterns
        hour = current_time.hour
        base_usage = 15  # Base idle usage
        
        # Higher usage during work hours
        if 9 <= hour <= 17:
            base_usage += 20
        
        # Add some random spikes and patterns
        if i % 60 < 30:  # Higher usage first half of each hour
            base_usage += 10
            
        # Random component
        noise = np.random.normal(0, 5)
        cpu_percent = max(5, min(95, base_usage + noise))
        
        # Occasional spikes
        if np.random.random() < 0.05:  # 5% chance of spike
            cpu_percent = min(95, cpu_percent + np.random.uniform(20, 40))
            
        cpu_usage.append(round(cpu_percent, 1))
    
    # Create DataFrame and save
    df = pd.DataFrame({
        'timestamp': timestamps,
        'cpu_percent': cpu_usage
    })
    
    df.to_csv(filename, index=False)
    print(f"✅ Sample data created: {filename}")
    return filename

if __name__ == "__main__":
    # Create sample data if file doesn't exist
    log_file = "data/cpu_log.csv"
    
    try:
        pd.read_csv(log_file)
        print(f"📁 Using existing data file: {log_file}")
    except FileNotFoundError:
        print("📝 Creating sample data...")
        create_sample_data(log_file)
    
    # Generate the enhanced visualization
    print("🎨 Generating enhanced CPU usage visualization...")
    stats = plot_usage(log_file)
    
    if stats:
        print("\n📊 Summary Statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")