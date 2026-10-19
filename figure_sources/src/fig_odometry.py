"""fig_odometry.pdf: extrusion synchronisation, filament odometry per print (July 2026 campaign).

(a) Net filament consumed per print (filled dot on a stem from zero) and the planned value as a horizontal
    tick where one exists:
      * two-rectangle attempt 3: planned 82.1 mm (fact sheet, section C, 2026-07-19 row);
      * C profile 0.8 mm bead: planned = 1.60 x the measured 0.5 mm C consumption, where 1.60 is the ratio of
        the two plans' extrusion.params.e_per_mm (C30_plan_w08.json / C30_plan_v2.json). It is a ratio
        prediction anchored on the measured 0.5 mm print, not an absolute plan total.
    No plan-side total exists for the other prints, so they carry no planned tick.
(b) Stall marks per print where they were counted (attempt 5: 13; v4, v5, v7: 0). "n/r" = not recorded.

Consumed / stall values are the campaign numbers of paper/vpp2026/FACT_SHEET.md (sections C and D), which
trace to HANDOFF_2026-07-16.md and the extrusion-scheduler memory log; they are entered here, not parsed.

Run:  . .venv/bin/activate && MPLBACKEND=Agg python paper/vpp2026/figs/src/fig_odometry.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import figstyle as fs  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use(os.environ.get("MPLBACKEND", "Agg"))
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

ROOT = Path(os.environ.get("ISAAC_WS_ROOT", HERE.parents[3]))
OUT = HERE.parent / "fig_odometry.pdf"

MI = "−"


def e_per_mm(plan_name):
    d = json.loads((ROOT / plan_name).read_text())
    return float(d["extrusion"]["params"]["e_per_mm"]), float(d["extrusion"]["params"]["line_width_mm"])


def main():
    fs.apply()
    e05, w05 = e_per_mm("C30_plan_v2.json")
    e08, w08 = e_per_mm("C30_plan_w08.json")
    assert (w05, w08) == (0.5, 0.8)
    plan_ratio = e08 / e05                      # 1.600

    # (label, group, consumed_mm, planned_mm or None, stall_marks or None)
    prints = [
        ("Att. 3", "rect", 82.35, 82.1, None),
        ("Att. 5", "rect", 562.0, None, 13),
        ("v4", "rect", 557.0, None, 0),
        ("v5", "rect", 573.6, None, 0),
        ("v7", "rect", 572.1, None, 0),
        ("0.5 mm", "C", 1006.0, None, None),
        ("0.8 mm", "C", 1593.0, None, None),
    ]
    c05 = prints[5][2]
    prints[6] = (*prints[6][:3], plan_ratio * c05, None)
    meas_ratio = prints[6][2] / c05

    gap = 0.7
    x = np.array([0, 1, 2, 3, 4, 4 + 1 + gap, 4 + 2 + gap], dtype=float)
    consumed = np.array([p[2] for p in prints])

    fig_h = 2.35
    fig = plt.figure(figsize=(fs.COL_W_IN, fig_h))
    left, width = 0.155, 0.83
    ax = fig.add_axes([left, 0.375, width, 0.58])
    axs = fig.add_axes([left, 0.135, width, 0.18], sharex=ax)

    # ---------------- (a) consumed vs planned ----------------
    ax.yaxis.grid(True, color=fs.GRID, lw=0.5)
    ax.set_axisbelow(True)
    for xi, p in zip(x, prints):
        ax.plot([xi, xi], [0, p[2]], color=fs.SERIES_1, lw=1.0, solid_capstyle="butt", zorder=2)
        if p[3] is not None:
            ax.plot([xi - 0.30, xi + 0.30], [p[3], p[3]], color=fs.SERIES_2, lw=1.8,
                    solid_capstyle="butt", zorder=3)
    ax.plot(x, consumed, "o", ms=4.6, mfc=fs.SERIES_1, mec=fs.SURFACE, mew=0.9, zorder=4)

    # Direct value labels (seven values, the figure doubles as the table view)
    for i, (xi, p) in enumerate(zip(x, prints)):
        if i == 0:
            continue
        lab = f"{p[2]:.1f}" if p[2] % 1 else f"{p[2]:,.0f}"
        if i == 5:   # left of the dot, so the scaling arrow leaves it clear
            ax.annotate(lab, (xi, p[2]), xytext=(-5, 0), textcoords="offset points",
                        ha="right", va="center", fontsize=6.3, color=fs.INK)
        else:
            ax.annotate(lab, (xi, p[2]), xytext=(0, 4.5), textcoords="offset points",
                        ha="center", va="bottom", fontsize=6.3, color=fs.INK)
    # Attempt 3: consumed vs planned, error
    p3 = prints[0]
    err = (p3[2] - p3[3]) / p3[3] * 100
    ax.annotate(f"{p3[2]:.2f}\nplan {p3[3]:.1f}\n(+{err:.1f} %)", (x[0], p3[2]), xytext=(0, 5),
                textcoords="offset points", ha="center", va="bottom", fontsize=6.0, color=fs.INK,
                linespacing=1.0)
    # 0.8 / 0.5 scaling
    ax.annotate("", xy=(x[6] - 0.07, consumed[6] - 30), xytext=(x[5] + 0.12, consumed[5] + 15),
                arrowprops=dict(arrowstyle="-|>", color=fs.INK_2, lw=0.7, mutation_scale=6,
                                shrinkA=2.5, shrinkB=3.5, connectionstyle="arc3,rad=-0.25"))
    ax.text(x[5] - 0.2, 1420, f"×{meas_ratio:.2f}\n(plan ×{plan_ratio:.2f})", ha="right",
            va="center", fontsize=6.3, color=fs.INK, linespacing=1.0)

    ax.set_ylim(0, 1800)
    ax.set_yticks([0, 500, 1000, 1500])
    ax.set_yticklabels(["0", "500", "1,000", "1,500"])
    ax.set_ylabel("Net filament (mm)", labelpad=2)
    ax.tick_params(axis="x", length=0, labelbottom=False)
    ax.spines["bottom"].set_color(fs.AXIS)
    handles = [
        Line2D([], [], ls="none", marker="o", ms=4.6, mfc=fs.SERIES_1, mec=fs.SURFACE, mew=0.9,
               label="Consumed"),
        Line2D([], [], color=fs.SERIES_2, lw=1.8, solid_capstyle="butt", label="Planned"),
    ]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 1.0), handlelength=1.1,
              handletextpad=0.35, labelspacing=0.3, borderaxespad=0.1)
    fig.text(0.012, 0.985, "(a)", ha="left", va="top", fontsize=8, fontweight="bold", color=fs.INK)

    # ---------------- (b) stall marks ----------------
    axs.yaxis.grid(True, color=fs.GRID, lw=0.5)
    axs.set_axisbelow(True)
    for xi, p in zip(x, prints):
        if p[4] is None:
            axs.text(xi, 1.5, "n/r", ha="center", va="bottom", fontsize=6.0, color=fs.MUTED,
                     style="italic")
            continue
        axs.plot([xi, xi], [0, p[4]], color=fs.SERIES_1, lw=1.0, solid_capstyle="butt", zorder=2)
        axs.plot([xi], [p[4]], "o", ms=4.6, mfc=fs.SERIES_1, mec=fs.SURFACE, mew=0.9, zorder=4,
                 clip_on=False)
        axs.annotate(f"{p[4]}", (xi, p[4]), xytext=(0, 3.5), textcoords="offset points",
                     ha="center", va="bottom", fontsize=6.3, color=fs.INK)
    axs.set_ylim(0, 18)
    axs.set_yticks([0, 5, 10, 15])
    axs.set_ylabel("Stall\nmarks", labelpad=2, linespacing=0.95)
    axs.set_xticks(x)
    axs.set_xticklabels([p[0] for p in prints])
    axs.tick_params(axis="x", length=0, pad=2.5)
    axs.set_xlim(x[0] - 0.6, x[-1] + 0.6)
    fig.text(0.012, 0.335, "(b)", ha="left", va="top", fontsize=8, fontweight="bold", color=fs.INK)

    # Group labels under the tick labels
    ytxt = -0.40
    for lo, hi, name in ((x[0], x[4], "Two-rectangle article"), (x[5], x[6], "C profile (bead)")):
        mid = (lo + hi) / 2
        axs.annotate("", xy=(lo - 0.3, ytxt), xytext=(hi + 0.3, ytxt),
                     xycoords=("data", "axes fraction"), textcoords=("data", "axes fraction"),
                     arrowprops=dict(arrowstyle="-", color=fs.AXIS, lw=0.6))
        axs.text(mid, ytxt - 0.07, name, transform=axs.get_xaxis_transform(), ha="center", va="top",
                 fontsize=6.8, color=fs.INK_2)

    fig.savefig(OUT)
    print(f"wrote {OUT}")
    print(f"  e_per_mm 0.5={e05:.6f} 0.8={e08:.6f} plan ratio={plan_ratio:.4f}; measured ratio="
          f"{meas_ratio:.4f}; C 0.8 planned-by-ratio={plan_ratio * c05:.1f} mm; att.3 error={err:.2f} %")


if __name__ == "__main__":
    main()
