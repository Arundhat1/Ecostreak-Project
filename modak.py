import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO

st.set_page_config(page_title="IFS Modak Explorer", layout="wide")
st.title("IFS Modak Explorer ")
st.write("Turn randomness into a Modak! Adjust transforms, probabilities, and colors.")

# --- Default transforms for a Modak shape ---
default_transforms = [
     [0.72, 0.03, 0.03, 0.68, 0.00, 0.30, 0.60],  # f1: Softer, Rounder Top
    [0.50, -0.18, 0.18, 0.50, 0.00, 0.25, 0.13],  # f2: Pronounced Right Pleat
    [0.50, 0.18, -0.18, 0.50, 0.00, 0.25, 0.13],  # f3: Pronounced Left Pleat
    [0.55, 0.00, 0.00, 0.45, 0.00, 0.20, 0.14]
]
default_probs = [0.60, 0.13, 0.13, 0.14]

# --- Sidebar controls ---
st.sidebar.header("Controls")
color = st.sidebar.color_picker("Pick your Modak color", "#800080")
num_points = st.sidebar.slider("Number of points", 10000, 100000, 50000, step=5000)

# Transform sliders
transforms = []
st.sidebar.subheader("Transform Parameters")
for i in range(4):
    st.sidebar.markdown(f"**Transform {i+1}**")
    a = st.sidebar.slider(f"a{i+1}", -1.0, 1.0, default_transforms[i][0], 0.01)
    b = st.sidebar.slider(f"b{i+1}", -1.0, 1.0, default_transforms[i][1], 0.01)
    c = st.sidebar.slider(f"c{i+1}", -1.0, 1.0, default_transforms[i][2], 0.01)
    d = st.sidebar.slider(f"d{i+1}", -1.0, 1.0, default_transforms[i][3], 0.01)
    e = st.sidebar.slider(f"e{i+1}", -1.0, 1.0, default_transforms[i][4], 0.01)
    f = st.sidebar.slider(f"f{i+1}", -1.0, 1.0, default_transforms[i][5], 0.01)
    transforms.append((a, b, c, d, e, f))

# Probability sliders
st.sidebar.subheader("Probabilities")
probs = []
for i in range(4):
    p = st.sidebar.slider(f"Probability {i+1}", 0.0, 1.0, default_probs[i], 0.01)
    probs.append(p)
probs = np.array(probs)
probs = probs / probs.sum()

# --- Generate IFS points ---
def generate_points(transforms, probs, n=50000):
    x, y = 0, 0
    xs, ys = [], []
    for _ in range(n):
        t = np.random.choice(len(transforms), p=probs)
        a, b, c, d, e, f = transforms[t]
        x, y = a*x + b*y + e, c*x + d*y + f
        xs.append(x)
        ys.append(y)
    return xs, ys

xs, ys = generate_points(transforms, probs, num_points)

# --- Plot ---
fig, ax = plt.subplots(figsize=(6, 8))
ax.scatter(xs, ys, s=0.1, color=color)
ax.set_axis_off()
st.pyplot(fig)

# --- Download button ---
def fig_to_bytes(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=300)
    buf.seek(0)
    return buf

st.download_button(
    "Download your Modak ",
    data=fig_to_bytes(fig),
    file_name="modak.png",
    mime="image/png"
)

# --- Instructions ---
st.markdown("""
**Instructions:**  
- Adjust transform sliders to see how your Modak shape changes.  
- Change probabilities to control frequency of each leaf/stem.  
- Pick any color you like!  
- Use the download button to save your Modak.  
Happy experimenting! 
""")
