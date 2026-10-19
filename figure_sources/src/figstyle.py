"""Shared matplotlib style for the VPP 2026 manuscript figures (Taylor & Francis, Interact class).

Single-column width 3.3 in, Times-metric serif (Liberation Serif, metric-compatible with Times New Roman),
TrueType font embedding (pdf.fonttype 42) so the PDF passes journal font checks.

Colour roles follow the dataviz reference palette (validated with validate_palette.js on a white surface,
slots 1 and 2: all checks PASS, worst CVD dE 24.7, normal-vision dE 33.6). Every colour distinction is
duplicated by a marker shape or fill (filled vs open), so the figures stay legible in grayscale.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

COL_W_IN = 3.3

# Categorical slots (dataviz reference palette, light mode)
SERIES_1 = "#2a78d6"   # blue: measured / primary series
SERIES_2 = "#eb6834"   # orange: planned / secondary series
# Ink and chrome
INK = "#0b0b0b"
INK_2 = "#52514e"      # secondary text
MUTED = "#898781"      # axis labels of lesser rank, n/r text
GRID = "#e1e0d9"
AXIS = "#9c9b94"       # one step darker than the reference baseline so it survives print
SURFACE = "#ffffff"

# Diverging ramp for signed residuals: blue (below plane) <-> neutral gray <-> red (above plane).
# Blue arm = reference sequential blue steps 600 / 300 (OKLab L 0.433 / 0.717); red arm = the reference
# red slot (#e34948) hue re-stepped in OKLCH to the same two lightnesses (#e5847d L 0.717, #8e2526 L 0.433),
# so equal |residual| reads as equal darkness on both sides (and in grayscale). Midpoint = reference gray.
DIVERGING = LinearSegmentedColormap.from_list(
    "resid_div",
    [(0.00, "#184f95"), (0.25, "#6da7ec"), (0.50, "#f0efec"), (0.75, "#e5847d"), (1.00, "#8e2526")],
)


def _register_serif() -> str:
    for cand in ("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"):
        if Path(cand).exists():
            font_manager.fontManager.addfont(cand)
    names = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Times New Roman", "Liberation Serif", "STIXGeneral"):
        if name in names:
            return name
    return "serif"


def apply() -> str:
    family = _register_serif()
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": [family, "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "custom",
        "mathtext.rm": f"{family}",
        "mathtext.it": f"{family}:italic",
        "mathtext.bf": f"{family}:bold",
        "mathtext.cal": f"{family}:italic",
        "mathtext.sf": f"{family}",
        "font.size": 7.5,
        "axes.labelsize": 7.5,
        "axes.titlesize": 7.5,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 6.5,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 0.6,
        "axes.labelcolor": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "grid.color": GRID,
        "grid.linewidth": 0.5,
        "grid.linestyle": "-",
        "xtick.color": AXIS,
        "ytick.color": AXIS,
        "xtick.labelcolor": INK,
        "ytick.labelcolor": INK,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "xtick.major.pad": 2,
        "ytick.major.pad": 2,
        "legend.frameon": False,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.dpi": 600,
        "lines.solid_capstyle": "round",
    })
    return family


def panel_label(ax, text, x=-0.02, y=1.02):
    """Small bold (a)/(b) tag at the top-left corner of an axes (not a title)."""
    ax.text(x, y, text, transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, fontweight="bold", color=INK)
