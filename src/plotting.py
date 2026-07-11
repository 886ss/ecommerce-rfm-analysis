"""Shared plotting utilities — backend setup, colour palette, save helper."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Segment colour palette ──
SEGMENT_COLORS: dict[str, str] = {
    "Champions": "#2ecc71",
    "Loyal Customers": "#3498db",
    "Potential Loyalists": "#9b59b6",
    "At Risk": "#f39c12",
    "Needs Attention": "#e74c3c",
    "New Customers": "#1abc9c",
    "About to Sleep": "#e67e22",
    "Promising": "#2c3e50",
    "Hibernating": "#95a5a6",
    "Lost": "#bdc3c7",
}

# Fallback list for non-segment-specific plots (funnel etc.)
PALETTE_10 = [
    "#2ecc71", "#3498db", "#9b59b6", "#f39c12", "#e74c3c",
    "#1abc9c", "#e67e22", "#95a5a6", "#34495e", "#7f8c8d",
]


def save_chart(fig: plt.Figure, output_dir: str | Path, filename: str,
               dpi: int = 150) -> Path:
    """Save figure to output_dir, close it, and return the saved path."""
    path = Path(output_dir) / filename
    fig.tight_layout()
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path
