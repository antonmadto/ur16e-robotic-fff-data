#!/usr/bin/env python3
"""Thermal-twin preview figure for the C_30mm plan (C30_plan_v2.json).

Runs the project's thermal digital twin (twin/thermal_fem.py + twin/bond_model.py)
OFFLINE through its Python API, file to file: no server, no robot, no Jetson.

Two figures, same data:
  --variant spec     -> figs/fig_thermal.pdf
      (a) developed (unrolled) cylinder wall, one rectangle per bead element at
          its centroid, coloured by per-element peak temperature
      (b) per-layer median relative bond index B_rel (IQR shaded) at the default
          tw_ref = 0.02 s and at the upper end of the plausible range, 0.1 s
  --variant contact  -> figs/fig_thermal_contact.pdf  (recommended alternative)
      (a) per-layer substrate temperature when the next bead lands (median, IQR)
      (b) per-layer critical weld time t_w* = int dt / a_T(T_int) over T_int > Tg,
          i.e. the largest tw_ref at which the interface still heals fully (D_h = 1)

Usage (from the repo root, venv active):
    MPLBACKEND=Agg python paper/vpp2026/figs/src/fig_thermal.py --variant both \
        [--cache /path/to/cache.npz] [--recompute]

The bed plane used for layer assignment is bed_calibration_creality_20260721_retired.json,
the calibration the plan was built against (2026-07-21) and the one in place when the
twin was validated (2026-08-09): it reproduces 10,625 elements / 167 layers / 21,027 edges.
The current bed_calibration.json (MK52 bed, 2026-09-16) gives 168 layers for this plan.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("ISAAC_WS_ROOT", HERE.parents[3]))
sys.path.insert(0, str(ROOT))

PLAN = ROOT / "C30_plan_v2.json"
BED_CAL = ROOT / "bed_calibration_creality_20260721_retired.json"
TW_REF_HIGH = 0.1          # s, upper end of the plausible tw_ref range (thermal_fem.TwinConfig)
TW_RANGE = (1e-3, 1e-1)    # s, plausible tw_ref range quoted in twin/thermal_fem.py


# --------------------------------------------------------------------- compute
def _run(cfg, plan, bed_cal, diagnostics: bool):
    """One replay to print end + 30 s cool-down (same horizon as run_headless)."""
    from twin.thermal_fem import ThermalGraph, ThermalSim
    from twin.bond_model import shift_factor

    t0 = time.perf_counter()
    g = ThermalGraph(plan, cfg, bed_cal)
    t_build = time.perf_counter() - t0
    sim = ThermalSim(g, cfg)
    nz = len(g.z_edges)
    T_sub = np.full(nz, np.nan)          # substrate (lower element) T just before contact
    H = np.zeros(nz)                     # uncapped healing integral int dt / a_T(T_int)
    horizon = g.print_time + 30.0
    t0 = time.perf_counter()
    while sim.t < horizon:
        if diagnostics:
            T_before = sim.T.copy()
            alive_before = sim.bond.alive.copy()
        sim.step()
        if diagnostics:
            alive = sim.bond.alive
            new = alive & ~alive_before
            if new.any():
                T_sub[new] = T_before[g.zi[new]]
            # identical interface temperature and Tg gate to ThermalSim.step / BondState.step
            T_int = 0.5 * (sim.T[g.zi] + sim.T[g.zj])
            hot = alive & (T_int > sim.bond.m.Tg)
            if hot.any():
                H[hot] += sim.dt / shift_factor(T_int[hot], sim.bond.m)
    wall = time.perf_counter() - t0
    return g, sim, T_sub, H, t_build, wall


def compute() -> dict:
    from twin.thermal_fem import TwinConfig, load_plan

    plan = load_plan(PLAN)
    bed_cal = json.loads(BED_CAL.read_text())
    cfg = TwinConfig.load()                          # twin/twin_config.json, tw_ref 0.02 s
    g, sim, T_sub, H, t_build, wall = _run(cfg, plan, bed_cal, diagnostics=True)

    cfg_hi = TwinConfig.load()
    cfg_hi.tw_ref = TW_REF_HIGH
    _, sim_hi, _, _, _, wall_hi = _run(cfg_hi, plan, bed_cal, diagnostics=False)

    # purge line: elements inside the plan's purge bounding box (+1 mm)
    pmin = np.asarray(plan["purge"]["world_min"]) - 1e-3
    pmax = np.asarray(plan["purge"]["world_max"]) + 1e-3
    purge = np.all((g.mid >= pmin) & (g.mid <= pmax), axis=1)

    o = np.asarray(bed_cal["plane"]["origin_m"], float)
    n = np.asarray(bed_cal["plane"]["normal"], float)
    n /= np.linalg.norm(n)
    h = (g.mid - o) @ n

    return dict(
        p0=g.p0, p1=g.p1, mid=g.mid, layer=g.layer, h=h, purge=purge,
        hl=g.hl, active=sim.active, T_peak=sim.T_peak,
        B_rel=sim.element_bond(relative=True), B_rel_hi=sim_hi.element_bond(relative=True),
        zi=g.zi, zj=g.zj, T_sub=T_sub, H=H,
        n_edges=len(g.ei), n_layers=g.n_layers, print_time=g.print_time, dt=sim.dt,
        T_dep=sim.T_dep, Tg=cfg.Tg, tw_ref=cfg.tw_ref,
        t_build=t_build, wall=wall, wall_hi=wall_hi,
    )


def load_or_compute(cache: Path | None, recompute: bool) -> dict:
    if cache and cache.exists() and not recompute:
        z = np.load(cache)
        return {k: (z[k].item() if z[k].ndim == 0 else z[k]) for k in z.files}
    d = compute()
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, **d)
    return d


def per_element_worst(d: dict, values: np.ndarray, fn) -> np.ndarray:
    """Per upper element, the worst value over its interfaces to the layer below
    (the twin's own display convention for the bond index)."""
    out = np.full(len(d["layer"]), np.nan)
    fn.at(out, d["zj"], values)
    return out


def per_layer_quartiles(layer: np.ndarray, v: np.ndarray, layers: np.ndarray):
    q = np.full((len(layers), 3), np.nan)
    for i, l in enumerate(layers):
        x = v[(layer == l) & np.isfinite(v)]
        if len(x):
            q[i] = np.percentile(x, [25, 50, 75])
    return q


def summary(d: dict) -> dict:
    act = d["active"]
    part = act & ~d["purge"]
    L = d["layer"]
    layers = np.arange(1, int(L.max()) + 1)
    Ts_el = per_element_worst(d, d["T_sub"], np.fmin)
    H_el = per_element_worst(d, d["H"], np.fmin)
    qB = per_layer_quartiles(L, d["B_rel"], layers)
    qBh = per_layer_quartiles(L, d["B_rel_hi"], layers)
    qT = per_layer_quartiles(L, Ts_el, layers)
    qH = per_layer_quartiles(L, H_el, layers)
    Bz = d["B_rel"][np.isfinite(d["B_rel"])]
    Bzh = d["B_rel_hi"][np.isfinite(d["B_rel_hi"])]
    return {
        "elements": int(len(L)), "purge_elements": int(d["purge"].sum()),
        "part_elements": int(part.sum()), "layers": int(d["n_layers"]),
        "edges": int(d["n_edges"]), "interlayer_interfaces": int(len(d["zi"])),
        "print_time_s": round(float(d["print_time"]), 1), "dt_s": float(d["dt"]),
        "graph_build_s": round(float(d["t_build"]), 3),
        "replay_wall_s_default_with_diagnostics": round(float(d["wall"]), 1),
        "replay_wall_s_tw_ref_0.1": round(float(d["wall_hi"]), 1),
        "T_dep_C": float(d["T_dep"]),
        "T_peak_median_all_C": round(float(np.median(d["T_peak"][act])), 2),
        "T_peak_median_part_C": round(float(np.median(d["T_peak"][part])), 2),
        "T_peak_min_max_part_C": [round(float(d["T_peak"][part].min()), 2),
                                  round(float(d["T_peak"][part].max()), 2)],
        "B_rel_default_min_median": [round(float(Bz.min()), 4), round(float(np.median(Bz)), 4)],
        "B_rel_default_frac_below_1": round(float((Bz < 0.999).mean()), 4),
        "B_rel_tw0.1_min_median": [round(float(Bzh.min()), 4), round(float(np.median(Bzh)), 4)],
        "B_rel_tw0.1_layers_median_below_1": [int(l) for l, q in zip(layers, qBh) if q[1] < 0.999],
        "B_rel_tw0.1_layer1_median": round(float(qBh[0, 1]), 3),
        "T_sub_contact_median_C_layers_1_2_3_8_steady": [round(float(qT[i, 1]), 1) for i in (0, 1, 2, 7)]
        + [round(float(np.nanmedian(qT[20:, 1])), 1)],
        "T_sub_contact_min_max_C": [round(float(np.nanmin(d["T_sub"])), 1),
                                    round(float(np.nanmax(d["T_sub"])), 1)],
        "t_w_star_median_s_layers_1_2_steady": [round(float(qH[0, 1]), 3), round(float(qH[1, 1]), 3),
                                                round(float(np.nanmedian(qH[20:, 1])), 3)],
        "t_w_star_min_s": round(float(np.nanmin(d["H"])), 4),
        "t_w_star_min_s_layers_ge_2": round(float(np.nanmin(H_el[L >= 2])), 3),
        "B_rel_default_layers_median_below_1": [int(l) for l, q in zip(layers, qB) if q[1] < 0.999],
    }


# ------------------------------------------------------------------------ plot
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#898781"
BAND_NEUTRAL = "#f0efec"
S1 = "#2a78d6"   # categorical slot 1 (blue)
S2 = "#eb6834"   # categorical slot 2 (orange)


def style():
    import matplotlib as mpl
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": ["STIXGeneral", "Nimbus Roman", "Liberation Serif", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5,
        "axes.edgecolor": AXIS, "axes.linewidth": 0.6, "axes.labelcolor": INK,
        "xtick.color": AXIS, "ytick.color": AXIS,
        "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.minor.width": 0.4, "ytick.minor.width": 0.4,
        "xtick.major.size": 3, "ytick.major.size": 3,
        "xtick.minor.size": 1.8, "ytick.minor.size": 1.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "pdf.fonttype": 42, "ps.fonttype": 42,
        "savefig.dpi": 600,
    })


def heat_cmap():
    """Semantic heat ramp (ColorBrewer YlOrRd, truncated so the low end stays visible
    on white). OKLab lightness falls monotonically, about 0.91 -> 0.40: grayscale-legible and
    CVD-safe (one lightness direction carries the magnitude)."""
    import matplotlib as mpl
    from matplotlib.colors import LinearSegmentedColormap
    base = mpl.colormaps["YlOrRd"]
    return LinearSegmentedColormap.from_list("heat", base(np.linspace(0.22, 1.0, 256)))


FIG_W = 6.5      # in
BOT, TOP = 0.42, 0.24   # in, below / above the plot boxes
AX_H = 1.40      # in, plot-box height shared by both panels


def _axes_in(fig, left, bottom, width, height):
    W, H = fig.get_size_inches()
    return fig.add_axes([left / W, bottom / H, width / W, height / H])


def _layer_axis(ax, n_max):
    from matplotlib.ticker import FixedLocator, NullFormatter
    ax.set_xscale("log")
    ax.set_xlim(0.88, n_max * 1.1)
    ticks = [1, 2, 5, 10, 20, 50, 100]
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.set_xticklabels([str(t) for t in ticks])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel(f"Layer number (log scale, 1 to {n_max})")


def _panel_label(ax, s):
    ax.annotate(s, xy=(0, 1), xycoords="axes fraction", xytext=(-34, 4),
                textcoords="offset points", ha="left", va="bottom",
                fontsize=9, fontweight="bold", color=INK)


def wall_geometry(d):
    """Unrolled cylinder wall: each bead element becomes a rectangle spanning its
    arc (p0 -> p1) and one layer height, centred on its centroid. Returns the
    rectangles in mm, the kept-element mask, and the extents."""
    keep = d["active"] & ~d["purge"]
    mid, p0, p1 = d["mid"][keep], d["p0"][keep], d["p1"][keep]
    c = mid[:, :2].mean(axis=0)
    R = float(np.median(np.hypot(mid[:, 0] - c[0], mid[:, 1] - c[1])))
    circ = 2 * np.pi * R
    s0 = (np.arctan2(p0[:, 1] - c[1], p0[:, 0] - c[0]) + np.pi) * R
    s1 = (np.arctan2(p1[:, 1] - c[1], p1[:, 0] - c[0]) + np.pi) * R
    s1 = np.where(s1 - s0 > circ / 2, s1 - circ, np.where(s0 - s1 > circ / 2, s1 + circ, s1))
    h = d["h"][keep]
    h = h - h.min()
    hl = float(d["hl"])
    lo, hi = np.minimum(s0, s1), np.maximum(s0, s1)
    y0, y1 = h - hl / 2, h + hl / 2
    verts = np.stack([np.c_[lo, y0], np.c_[hi, y0], np.c_[hi, y1], np.c_[lo, y1]], axis=1) * 1e3
    ext = (0.0, circ * 1e3, -hl * 1e3 / 2, (h.max() + hl / 2) * 1e3)
    return verts, keep, ext, R


def fig_spec(d: dict, out: Path):
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import Normalize
    style()
    verts, keep, ext, R = wall_geometry(d)
    map_w = AX_H * (ext[1] - ext[0]) / (ext[3] - ext[2])      # equal aspect, in
    fig = plt.figure(figsize=(FIG_W, BOT + AX_H + TOP))
    left_a = 0.46
    ax_a = _axes_in(fig, left_a, BOT, map_w, AX_H)
    cax = _axes_in(fig, left_a + map_w + 0.07, BOT, 0.07, AX_H)
    left_b = left_a + map_w + 1.25
    ax_b = _axes_in(fig, left_b, BOT, FIG_W - left_b - 0.08, AX_H)

    norm = Normalize(vmin=205.7, vmax=206.9)
    pc = PolyCollection(verts, array=d["T_peak"][keep], cmap=heat_cmap(), norm=norm,
                        edgecolors="none", linewidths=0, antialiaseds=False, rasterized=True)
    ax_a.add_collection(pc)
    ax_a.set_xlim(ext[0], ext[1])
    ax_a.set_ylim(ext[2], ext[3])
    ax_a.set_xticks([0, 20, 40, 60, 80])
    ax_a.set_yticks([0, 10, 20, 30, 40, 50])
    ax_a.set_xlabel("Circumferential position (mm)")
    ax_a.set_ylabel("Height (mm)")
    cb = fig.colorbar(pc, cax=cax)
    cb.set_label("Peak temperature (°C)", labelpad=4)
    cb.set_ticks([205.8, 206.0, 206.2, 206.4, 206.6, 206.8])
    cb.outline.set_linewidth(0.4)
    cb.outline.set_edgecolor(AXIS)
    cb.ax.tick_params(width=0.5, length=2.5, labelsize=7)
    _panel_label(ax_a, "(a)")

    L = d["layer"]
    n_max = int(L.max())
    layers = np.arange(1, n_max + 1)
    q = per_layer_quartiles(L, d["B_rel"], layers)
    qh = per_layer_quartiles(L, d["B_rel_hi"], layers)
    ax = ax_b
    ax.axhline(0.6, color=MUTED, lw=0.6, zorder=1)
    ax.text(n_max * 1.05, 0.6 - 0.03, "weak-bond flag 0.6", color=INK2, fontsize=7,
            va="top", ha="right")
    ax.fill_between(layers, q[:, 0], q[:, 2], color=S1, alpha=0.15, lw=0, zorder=2)
    ax.fill_between(layers, qh[:, 0], qh[:, 2], color=S2, alpha=0.15, lw=0, zorder=2)
    ax.plot(layers, q[:, 1], color=S1, lw=1.5, solid_capstyle="round", zorder=3,
            label=r"$t_{w,\mathrm{ref}}$ = 0.02 s (default)")
    ax.plot(layers, qh[:, 1], color=S2, lw=1.5, ls=(0, (3.2, 1.8)), dash_capstyle="round", zorder=4,
            label=r"$t_{w,\mathrm{ref}}$ = 0.1 s (upper bound)")
    ax.plot([1], [qh[0, 1]], "o", ms=4, color=S2, mec="white", mew=1.0, zorder=5)
    ax.annotate(f"layer 1: {qh[0, 1]:.2f}", xy=(1, qh[0, 1]), xytext=(8, -2),
                textcoords="offset points", ha="left", va="top", fontsize=7, color=INK2)
    _layer_axis(ax, n_max)
    ax.set_ylim(0, 1.1)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_ylabel(r"Relative bond index $B_\mathrm{rel}$")
    ax.yaxis.grid(True, color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", frameon=False, handlelength=2.6, borderaxespad=0.1,
              labelcolor=INK)
    _panel_label(ax, "(b)")
    fig.savefig(out, metadata={"Title": "Thermal twin preview, C_30mm", "Creator": "fig_thermal.py"})
    plt.close(fig)


def fig_contact(d: dict, out: Path):
    import matplotlib.pyplot as plt
    style()
    fig = plt.figure(figsize=(FIG_W, BOT + AX_H + TOP))
    w = 2.55
    ax_a = _axes_in(fig, 0.50, BOT, w, AX_H)
    ax_b = _axes_in(fig, FIG_W - 0.08 - w, BOT, w, AX_H)
    L = d["layer"]
    n_max = int(L.max())
    layers = np.arange(1, n_max + 1)

    Ts = per_element_worst(d, d["T_sub"], np.fmin)
    q = per_layer_quartiles(L, Ts, layers)
    ax = ax_a
    Tg = float(d["Tg"])
    ax.axhline(Tg, color=MUTED, lw=0.6, zorder=1)
    ax.text(n_max * 1.05, Tg - 2, f"$T_g$ = {Tg:.0f} °C", color=INK2, fontsize=7,
            ha="right", va="top")
    ax.fill_between(layers, q[:, 0], q[:, 2], color=S1, alpha=0.15, lw=0, zorder=2)
    ax.plot(layers, q[:, 1], color=S1, lw=1.5, zorder=3)
    ax.plot([1], [q[0, 1]], "o", ms=4, color=S1, mec="white", mew=1.0, zorder=4)
    ax.annotate(f"{q[0, 1]:.0f} °C", xy=(1, q[0, 1]), xytext=(7, 4),
                textcoords="offset points", ha="left", va="bottom", fontsize=7, color=INK2)
    steady = float(np.nanmedian(q[20:, 1]))
    ax.annotate(f"{steady:.0f} °C", xy=(12, q[11, 1]), xytext=(0, 5),
                textcoords="offset points", ha="center", va="bottom", fontsize=7, color=INK2)
    _layer_axis(ax, n_max)
    ax.set_ylim(40, 125)
    ax.set_ylabel("Substrate T at contact (°C)")
    ax.yaxis.grid(True, color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    _panel_label(ax, "(a)")

    H = per_element_worst(d, d["H"], np.fmin)
    qh = per_layer_quartiles(L, H, layers)
    ax = ax_b
    ax.set_yscale("log")
    ax.axhspan(*TW_RANGE, color=BAND_NEUTRAL, lw=0, zorder=0)
    ax.text(n_max * 1.05, TW_RANGE[0] * 1.3, r"plausible $t_{w,\mathrm{ref}}$ range",
            color=INK2, fontsize=7, ha="right", va="bottom")
    ax.axhline(float(d["tw_ref"]), color=INK2, lw=0.6, zorder=1)
    ax.text(n_max * 1.05, float(d["tw_ref"]) * 0.85, r"default $t_{w,\mathrm{ref}}$ = 0.02 s",
            color=INK2, fontsize=7, ha="right", va="top")
    ax.fill_between(layers, qh[:, 0], qh[:, 2], color=S1, alpha=0.15, lw=0, zorder=2)
    ax.plot(layers, qh[:, 1], color=S1, lw=1.5, zorder=3)
    ax.plot([1], [qh[0, 1]], "o", ms=4, color=S1, mec="white", mew=1.0, zorder=4)
    ax.annotate(f"{qh[0, 1]:.3f} s", xy=(1, qh[0, 1]), xytext=(7, 0),
                textcoords="offset points", ha="left", va="center", fontsize=7, color=INK2)
    _layer_axis(ax, n_max)
    ax.set_ylim(5e-4, 3)
    ax.set_ylabel(r"Critical weld time $t_w^{*}$ (s)")
    ax.yaxis.grid(True, which="major", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    _panel_label(ax, "(b)")
    fig.savefig(out, metadata={"Title": "Thermal twin contact preview, C_30mm", "Creator": "fig_thermal.py"})
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--variant", choices=["spec", "contact", "both"], default="both")
    ap.add_argument("--cache", type=Path, default=None, help="npz cache of the twin run")
    ap.add_argument("--recompute", action="store_true")
    ap.add_argument("--outdir", type=Path, default=HERE.parent)
    args = ap.parse_args()
    t0 = time.perf_counter()
    d = load_or_compute(args.cache, args.recompute)
    print(json.dumps(summary(d), indent=1))
    if args.variant in ("spec", "both"):
        fig_spec(d, args.outdir / "fig_thermal.pdf")
    if args.variant in ("contact", "both"):
        fig_contact(d, args.outdir / "fig_thermal_contact.pdf")
    print(f"total wall {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()
