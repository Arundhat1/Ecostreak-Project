import numpy as np
import matplotlib.pyplot as plt
import random

num_points = 200000

# Define the SURGICALLY REFINED IFS rules for the Modak
modak_rules = [
    [0.72, 0.03, 0.03, 0.68, 0.00, 0.30, 0.60],  # f1: Softer, Rounder Top
    [0.50, -0.18, 0.18, 0.50, 0.00, 0.25, 0.13],  # f2: Pronounced Right Pleat
    [0.50, 0.18, -0.18, 0.50, 0.00, 0.25, 0.13],  # f3: Pronounced Left Pleat
    [0.55, 0.00, 0.00, 0.45, 0.00, 0.20, 0.14]    # f4: Wider Base
]

# Convert rules to numpy array and extract probabilities
rules_array = np.array([r[:-1] for r in modak_rules])
probs = np.array([r[-1] for r in modak_rules])
probs /= np.sum(probs)

# Initialize arrays to store points
x = np.zeros(num_points)
y = np.zeros(num_points)
x[0], y[0] = 0, 0

# Iterate the IFS rules
for i in range(1, num_points):
    r = np.random.choice(len(modak_rules), p=probs)
    a, b, c, d, e, f = rules_array[r]
    x[i] = a * x[i-1] + b * y[i-1] + e
    y[i] = c * x[i-1] + d * y[i-1] + f

# Plotting
plt.figure(figsize=(5, 7))
plt.style.use('dark_background')
# Using a warm 'hot' colormap which goes from black -> red -> yellow, perfect for a modak
plt.scatter(x, y, s=0.07, c=y, cmap='hot', alpha=0.8, marker='.')
plt.axis('off')
plt.title('Surgically Refined Modak Fractal', color='white', fontsize=14)
plt.tight_layout()
plt.show()