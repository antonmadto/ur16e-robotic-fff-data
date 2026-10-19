"""fig_probe.pdf: force-guarded bed metrology, July 2026 campaign.

(a) 3x3 grid probe of 2026-07-21: per-point residual from the least-squares plane through the nine contacts
    (field points[].residual_mm of bed_probe_9pt_20260721.json; re-derived here from z_measured_m and
    checked against the stored value).
(b) Probe-session series 2026-07-20 to 07-23: mean height delta per session with the min..max spread of the
    per-point deltas as whiskers.
    * filled circles: delta vs the ORIGINAL 2026-07-14 calibration plane (plane block of
      bed_calibration.json.bak-20260721). For 07-20 and the 9-pt grid this is the stored delta_mm; for the
      three later sessions it is recomputed from z_measured_m, because those files store delta_mm against the
      9-pt re-fitted plane that became the active calibration on 2026-07-21 (their old_bed_calibration block
      keeps the 07-14 created_utc stamp but carries the re-fitted origin/normal).
    * open squares: the delta exactly as the pre-print probe recorded it (mean_delta_mm, vs the active
      re-fitted plane), for the three post re-fit sessions.
    * dashed lines: +-0.2 mm pre-print gate tolerance (tools/real_print.py, --probe-tol-mm).

Run:  . .venv/bin/activate && MPLBACKEND=Agg python paper/vpp2026/figs/src/fig_probe.py
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
OUT = HERE.parent / "fig_probe.pdf"

GRID_FILE = "bed_probe_9pt_20260721.json"
CAL_0714_FILE = "bed_calibration.json.bak-20260721"     # the 07-14 calibration as it was before the 9-pt re-fit
CAL_REFIT_FILE = "bed_calibration_20260721.json"         # the 9-pt re-fitted calibration (active from 07-21)
SESSIONS = [  # (file, x label)
    ("bed_probe_20260720.json", "S1\n1 pt"),
    ("bed_probe_5pt_20260720.json", "S2\n5 pt"),
    ("bed_probe_9pt_20260721.json", "S3\n9 pt"),
    ("bed_probe_20260721.json", "S4\n5 pt"),
    ("bed_probe_20260722.json", "S5\n5 pt"),
    ("bed_probe_20260723.json", "S6\n5 pt"),
]
GATE_TOL_MM = 0.2


def load(name):
    return json.loads((ROOT / name).read_text())


def plane_z_mm(plane, xy_mm):
    o = np.asarray(plane["origin_m"]) * 1000.0
    n = np.asarray(plane["normal"])
    return o[2] - (n[0] * (xy_mm[0] - o[0]) + n[1] * (xy_mm[1] - o[1])) / n[2]


def same_plane(a, b, tol=1e-9):
    return (np.allclose(a["origin_m"], b["origin_m"], atol=tol)
            and np.allclose(a["normal"], b["normal"], atol=tol))


def grid_residuals():
    d = load(GRID_FILE)
    pts = [p for p in d["points"] if p["ok"]]
    assert len(pts) == 9 and not d["aborted_early"]
    # Re-derive: least-squares plane z = a + b x + c y through the nine measured contacts.
    xy = np.array([p["xy_mm"] for p in pts])
    z = np.array([p["z_measured_m"] for p in pts]) * 1000.0
    A = np.c_[np.ones(len(z)), xy]
    coef, *_ = np.linalg.lstsq(A, z, rcond=None)
    vert = z - A @ coef                                     # vertical residual
    nz = 1.0 / np.sqrt(1 + coef[1] ** 2 + coef[2] ** 2)     # -> residual along the plane normal
    resid = vert * nz
    stored = np.array([p["residual_mm"] for p in pts])
    assert np.allclose(resid, stored, atol=1e-6), (resid, stored)
    grid = np.full((3, 3), np.nan)
    for p, r in zip(pts, stored):
        grid[p["row"], p["col"]] = r
    offs = sorted({p["offset_mm"][0] for p in pts})
    assert np.isclose(np.ptp(stored), d["flatness_pp_mm"])
    return grid, offs, d


def session_series():
    cal0714 = load(CAL_0714_FILE)["plane"]
    refit = load(CAL_REFIT_FILE)["plane"]
    rows = []
    for name, label in SESSIONS:
        d = load(name)
        pts = [p for p in d["points"] if p["ok"]]
        ref = d["old_bed_calibration"]
        zm = np.array([p["z_measured_m"] for p in pts]) * 1000.0
        rec = np.array([p["delta_mm"] for p in pts])
        # Re-derive the stored delta against the plane the file says it used (sanity check).
        chk = zm - np.array([plane_z_mm(ref, p["xy_mm"]) for p in pts])
        assert np.allclose(chk, rec, atol=1e-6)
        v0714 = zm - np.array([plane_z_mm(cal0714, p["xy_mm"]) for p in pts])
        if same_plane(ref, cal0714):
            ref_kind = "0714"
        elif same_plane(ref, refit):
            ref_kind = "refit"
        else:
            raise SystemExit(f"{name}: reference plane matches neither calibration")
        if "mean_delta_mm" in d:
            assert np.isclose(d["mean_delta_mm"], rec.mean())
        rows.append(dict(file=name, label=label, n=len(pts), ref=ref_kind,
                         rec_mean=rec.mean(), rec_min=rec.min(), rec_max=rec.max(),
                         v_mean=v0714.mean(), v_min=v0714.min(), v_max=v0714.max(),
                         flat=d.get("flatness_pp_mm"), tilt=d.get("tilt_mdeg_vs_old")))
    return rows


def main():
    fs.apply()
    grid, offs, gd = grid_residuals()
    rows = session_series()

    fig_h = 2.0
    fig = plt.figure(figsize=(fs.COL_W_IN, fig_h))
    # Left: square heat-grid (vertically centred on the series panel); right: session series.
    gw = 0.25
    gh = gw * fs.COL_W_IN / fig_h
    b_bottom, b_height = 0.205, 0.725
    g_bottom = b_bottom + b_height / 2 - gh / 2 + 0.06
    axg = fig.add_axes([0.155, g_bottom, gw, gh])
    axs = fig.add_axes([0.56, b_bottom, 0.43, b_height])

    # ---------------- (a) residual map ----------------
    vmax = 0.2
    step = offs[1] - offs[0]
    ext = [offs[0] - step / 2, offs[-1] + step / 2, offs[0] - step / 2, offs[-1] + step / 2]
    axg.imshow(grid, origin="lower", cmap=fs.DIVERGING, vmin=-vmax, vmax=vmax, extent=ext,
               interpolation="nearest")
    # 2 px surface gap between cells (white lines at the cell edges)
    for k in range(4):
        e = ext[0] + k * step
        axg.axvline(e, color=fs.SURFACE, lw=1.2)
        axg.axhline(e, color=fs.SURFACE, lw=1.2)
    cmap = fs.DIVERGING
    for r in range(3):
        for c in range(3):
            v = grid[r, c]
            rgba = cmap((v + vmax) / (2 * vmax))
            lum = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
            txt = f"{v:+.2f}".replace("-", "−")
            axg.text(offs[c], offs[r], txt, ha="center", va="center", fontsize=6.8,
                     color=fs.SURFACE if lum < 0.45 else fs.INK)
    axg.set_xticks(offs)
    axg.set_yticks(offs)
    axg.set_xticklabels([f"{o:.0f}".replace("-", "−") for o in offs])
    axg.set_yticklabels([f"{o:.0f}".replace("-", "−") for o in offs])
    axg.set_xlabel("Bed $x$ (mm)", labelpad=1.5)
    axg.set_ylabel("Bed $y$ (mm)", labelpad=1.0)
    for s in axg.spines.values():
        s.set_visible(False)
    axg.tick_params(length=0)
    axg.set_xlim(ext[0], ext[1])
    axg.set_ylim(ext[2], ext[3])
    axg.text(0.5, -0.43, f"Residual from plane (mm)\np–p {gd['flatness_pp_mm']:.2f} mm",
             transform=axg.transAxes, ha="center", va="top", fontsize=6.5, color=fs.INK_2,
             linespacing=1.05)
    fig.text(0.015, 0.975, "(a)", ha="left", va="top", fontsize=8, fontweight="bold", color=fs.INK)

    # ---------------- (b) session series ----------------
    x = np.arange(len(rows))
    axs.axhspan(-GATE_TOL_MM, GATE_TOL_MM, color="#f0efec", lw=0, zorder=0)
    for yv in (-GATE_TOL_MM, GATE_TOL_MM):
        axs.axhline(yv, color=fs.INK_2, lw=0.7, ls=(0, (3.5, 2)), zorder=1)
    axs.axhline(0, color=fs.AXIS, lw=0.5, zorder=1)
    axs.text(len(rows) - 0.55, GATE_TOL_MM + 0.03, "±0.2 mm gate", ha="right", va="bottom",
             fontsize=6.3, color=fs.INK_2)
    # Re-fit marker between the 9-pt grid and the next session
    xr = 2.5
    axs.axvline(xr, color=fs.MUTED, lw=0.6, ls=(0, (1, 1.5)), zorder=1)
    axs.text(xr + 0.08, 2.18, "9-pt plane\nadopted", ha="left", va="top", fontsize=6.0,
             color=fs.INK_2, linespacing=0.95)

    vm = np.array([r["v_mean"] for r in rows])
    vlo = vm - np.array([r["v_min"] for r in rows])
    vhi = np.array([r["v_max"] for r in rows]) - vm
    axs.errorbar(x, vm, yerr=[vlo, vhi], fmt="none", ecolor=fs.SERIES_1, elinewidth=0.9,
                 capsize=1.8, capthick=0.9, zorder=3)
    axs.plot(x, vm, "o", ms=4.0, mfc=fs.SERIES_1, mec=fs.SURFACE, mew=0.8, zorder=4)

    post = [i for i, r in enumerate(rows) if r["ref"] == "refit"]
    rm = np.array([rows[i]["rec_mean"] for i in post])
    rlo = rm - np.array([rows[i]["rec_min"] for i in post])
    rhi = np.array([rows[i]["rec_max"] for i in post]) - rm
    axs.errorbar(post, rm, yerr=[rlo, rhi], fmt="none", ecolor=fs.SERIES_2, elinewidth=0.9,
                 capsize=1.8, capthick=0.9, zorder=3)
    axs.plot(post, rm, "s", ms=3.6, mfc=fs.SURFACE, mec=fs.SERIES_2, mew=1.3, zorder=4)
    # Selective direct label: the last recorded session (the value quoted in the text)
    i_last = post[-1]
    axs.annotate(f"{rows[i_last]['rec_mean']:+.2f}".replace("-", "−"),
                 (i_last, rows[i_last]["rec_min"]), xytext=(0, -2.5), textcoords="offset points",
                 ha="center", va="top", fontsize=6.3, color=fs.INK)

    axs.set_xticks(x)
    axs.set_xticklabels([r["label"] for r in rows], linespacing=0.95)
    axs.set_xlim(-0.55, len(rows) - 0.45)
    axs.set_ylim(-0.95, 2.25)
    axs.set_yticks([-0.5, 0, 0.5, 1.0, 1.5, 2.0])
    axs.set_yticklabels(["−0.5", "0", "0.5", "1.0", "1.5", "2.0"])
    axs.set_ylabel("Mean height delta (mm)", labelpad=1.5)
    axs.tick_params(axis="x", length=0, pad=2.0)
    axs.set_xlabel("Probe session (in order)", labelpad=1.5)
    handles = [
        Line2D([], [], ls="none", marker="o", ms=4.0, mfc=fs.SERIES_1, mec=fs.SURFACE, mew=0.8,
               label="vs touch-off plane"),
        Line2D([], [], ls="none", marker="s", ms=3.6, mfc=fs.SURFACE, mec=fs.SERIES_2, mew=1.3,
               label="vs 9-pt plane"),
    ]
    axs.legend(handles=handles, loc="lower left", bbox_to_anchor=(-0.01, -0.02), handletextpad=0.2,
               borderaxespad=0.2, labelspacing=0.25, handlelength=1.0)
    fig.text(0.445, 0.975, "(b)", ha="left", va="top", fontsize=8, fontweight="bold", color=fs.INK)

    fig.savefig(OUT)
    print(f"wrote {OUT}")
    for r in rows:
        print(f"  {r['file']:32s} n={r['n']} ref={r['ref']:5s} vs0714 {r['v_mean']:+.3f} "
              f"[{r['v_min']:+.3f},{r['v_max']:+.3f}]  recorded {r['rec_mean']:+.3f} "
              f"[{r['rec_min']:+.3f},{r['rec_max']:+.3f}] flat={r['flat']} tilt_mdeg={r['tilt']}")


if __name__ == "__main__":
    main()
