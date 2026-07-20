# ecostreak/__init__.py
from .core.analyzer import analyze_usage
from .core.energy import estimate_energy
from .core.visualize import plot_usage

__all__ = ["analyze_usage", "estimate_energy", "plot_usage"]
