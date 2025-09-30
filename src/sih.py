import matplotlib.pyplot as plt

# Data points from survey findings (simplified labels)
labels = [
    "Ethiopia Univ.\nSatisfaction",
    "AI Tool Usage\n(US Colleges)",
    "Harvard\nAI Usage",
    "ChatGPT Use\n(US Colleges)",
    "Out-of-hours\nChatbot Demand",
    "Chatbot in\nCollege Search"
]

values = [70, 60, 90, 37, 59, 26]  # Approx % values

# Plot compact and aesthetic line/curve graph
plt.figure(figsize=(8,5))
plt.plot(labels, values, marker='o', linestyle='-', linewidth=2.5, markersize=8, color="#2E86C1")

# Formatting
plt.title("Student Survey Data: AI & Chatbot Usage in Education", fontsize=13, weight='bold')
plt.ylabel("Percentage of Students (%)", fontsize=11)
plt.xticks(rotation=20, ha="right", fontsize=9)
plt.yticks(fontsize=9)
plt.grid(True, linestyle='--', alpha=0.5)

# Annotate values
for i, val in enumerate(values):
    plt.text(i, val + 2, f"{val}%", ha='center', fontsize=9, color="#1B4F72")

# Compact layout for PPT
plt.tight_layout()
plt.show()