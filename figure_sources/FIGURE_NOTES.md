# Figure notes: fig_probe.pdf and fig_odometry.pdf

Generated 2026-10-07. Both figures are 3.3 in wide (single column), Liberation Serif (metric clone of Times New
Roman, TrueType embedded, pdf.fonttype 42), no title inside the figure, panel tags (a)/(b) only.
Colours: dataviz reference palette slot 1 blue `#2a78d6` and slot 2 orange `#eb6834` (validate_palette.js on a
white surface: all checks pass, worst CVD dE 24.7, normal-vision dE 33.6). Every colour distinction is doubled
by shape or fill (filled circle vs open square, dot vs horizontal tick; signed numbers in every heat-map cell),
so both figures read in grayscale (checked with `pdftoppm -gray`).

Rebuild (from the repo root):

```bash
cd ~/isaac_ws && . .venv/bin/activate && export MPLBACKEND=Agg
python paper/vpp2026/figs/src/fig_probe.py       # prints the derived numbers per session
python paper/vpp2026/figs/src/fig_odometry.py    # prints the e_per_mm ratio and the derived planned value
```

Scripts: `paper/vpp2026/figs/src/figstyle.py` (shared style), `fig_probe.py`, `fig_odometry.py`.

---

## fig_probe.pdf (bed metrology), 3.3 x 2.0 in

### Data sources (repo root)

| Use | File | Fields |
|---|---|---|
| (a) residual map | `bed_probe_9pt_20260721.json` | `points[].residual_mm`, `points[].row`, `points[].col`, `points[].offset_mm`, `flatness_pp_mm` |
| (a) cross-check | same | `points[].xy_mm`, `points[].z_measured_m` (plane re-fitted by least squares in the script; matches `residual_mm` to < 1e-6 mm) |
| (b) sessions | `bed_probe_20260720.json` (1 pt), `bed_probe_5pt_20260720.json`, `bed_probe_9pt_20260721.json`, `bed_probe_20260721.json`, `bed_probe_20260722.json`, `bed_probe_20260723.json` | `points[].ok`, `points[].delta_mm`, `points[].z_measured_m`, `points[].xy_mm`, `old_bed_calibration.origin_m/normal`, `mean_delta_mm` |
| (b) 07-14 reference plane | `bed_calibration.json.bak-20260721` | `plane.origin_m`, `plane.normal` (the 07-14 calibration as it stood before the 9-pt re-fit) |
| (b) re-fitted plane | `bed_calibration_20260721.json` | `plane.origin_m`, `plane.normal`, `probe` block (9-pt re-fit, active from 2026-07-21) |
| (b) gate tolerance | `tools/real_print.py` | `--probe-tol-mm` (0.2 mm; July rule "refuses on > 0.2 mm drift", memory log extrusion-scheduler-v2 2026-07-21) |

### Derivations

- **(a)** Residual = signed distance of each contact from the least-squares plane through the nine contacts
  (positive = above the plane). Grid laid out in the bed frame: `offset_mm` = (x, y) offset from the bed centre,
  row 0 = y -140 mm at the bottom. Values (mm): centre -0.132; row y = -140: +0.173, -0.155, +0.038;
  row y = 0: -0.123, -0.132, +0.144; row y = +140: +0.074, +0.040, -0.058. Peak-to-peak 0.328 mm.
- **(b) important finding: the six files do not share one reference.** The three files written after the
  9-pt grid (07-21 afternoon, 07-22, 07-23) carry an `old_bed_calibration` block that still says
  `created_utc 2026-07-14T07:04:39Z` but holds the 9-pt re-fitted origin/normal (origin z 95.090 mm instead of
  93.158 mm, normal equal to the 9-pt `plane_fit`). bed_probe.py copies the calibration's `created_utc`, and the
  re-fit kept the 07-14 stamp. So their `delta_mm` / `mean_delta_mm` are relative to the 9-pt plane, not to 07-14.
  The script verifies, per file, that `delta_mm` = `z_measured` - plane(`old_bed_calibration`) at `xy_mm`, and
  which of the two calibration files that plane equals.
- Filled circles = mean over the good points of `z_measured` minus the ORIGINAL 07-14 plane at the same `xy_mm`
  (identical to the stored `delta_mm` for the first three sessions; recomputed for the last three).
  Open squares = the stored `mean_delta_mm` of the last three sessions (vs the 9-pt plane), i.e. what the
  pre-print probe reported. Whiskers = min to max of the per-point deltas (not a standard deviation).

| Session (UTC) | File | n | vs 07-14 plane: mean [min, max] (mm) | as recorded: mean [min, max] (mm) | flatness_pp (mm) | tilt vs ref (mdeg) |
|---|---|---|---|---|---|---|
| 07-20 12:06 | bed_probe_20260720.json | 1 | +1.316 | same | n/a | n/a |
| 07-20 12:07 | bed_probe_5pt_20260720.json | 5 | +1.301 [+1.236, +1.387] | same | not stored | 35 |
| 07-21 06:19 | bed_probe_9pt_20260721.json | 9 | +1.522 [+1.083, +2.076] | same | 0.328 | 119 |
| 07-21 12:04 | bed_probe_20260721.json | 5 | +1.151 [+1.076, +1.205] | -0.371 [-0.454, -0.243] (vs 9-pt plane) | 0.107 | 157 |
| 07-22 07:34 | bed_probe_20260722.json | 5 | +1.087 [+1.061, +1.128] | -0.435 [-0.467, -0.388] (vs 9-pt plane) | 0.025 | 71 |
| 07-23 07:29 | bed_probe_20260723.json | 5 | +0.989 [+0.966, +1.004] | -0.533 [-0.599, -0.472] (vs 9-pt plane) | 0.016 | 111 |

- Footprints differ: the 07-20 5-pt rectangle spans about 123 x 83 mm, the 07-21 to 07-23 5-pt probes about
  50 x 50 mm around the bed centre, the 9-pt grid +-140 mm. The 9-pt whisker (1.0 mm wide) is mostly the 119 mdeg
  tilt between the stale 07-14 plane and the bed over the full grid, not noise.
- The +-0.2 mm dashed lines are drawn about zero. In July the gate compared the probe's recommended z translate
  with the translate the plan had been built on (`drift = rec - plan_t` in real_print.py before 2026-09-06), and
  plans were rebuilt at each probe's recommendation. The band therefore shows the tolerance scale (the window a
  plan built directly on the reference plane would have to meet), not the per-session gate verdicts.

### Not derivable from the files (left out of the figure)

- **Refusals.** No probe JSON records a gate verdict (no `refused`/`accepted` field; the July files hold one
  probe per day, later runs of the day overwrite earlier ones). The July refusals ("first live catch" 07-21,
  "drift 0.2 to 0.24 mm") live only in the memory log; the plan translate needed to recompute them is not in
  the probe files. No session is marked as refused.
- **Repeatability 27 um.** Not in any JSON (the repeat probe on 07-21 was overwritten); source is the memory
  log extrusion-scheduler-v2, 2026-07-21. Not plotted.

### Checks against the fact sheet (FACT_SHEET.md)

- 07-20: +1.30 mm, spread 0.15 mm (range 0.151), tilt 35 mdeg: **matches**.
- 07-21 9-pt: the file's mean delta is **+1.52 mm**, not +1.3 (the centre point alone reads +1.39 mm; +1.30 is
  the 07-20 5-pt mean). Central dip -0.13 mm and 119 mdeg: **match**. Suggest the text say "+1.5 mm (grid
  mean; +1.4 mm at the centre)".
- 07-23: mean delta -0.533 mm, flatness 0.0164 mm, tilt 111 mdeg: **match**, but this delta is relative to the
  07-21 9-pt plane, not to the 07-14 calibration (+0.99 mm vs 07-14).
- Fact sheet sections A and C give "planarity residual 0.173 mm, tilt 0.328 deg" for the **07-14** calibration.
  Those are the **07-21 re-fit** values (`bed_calibration_20260721.json`: planarity = max |9-pt residual|, tilt
  from the 9-pt normal). The 07-14 calibration itself (`bed_calibration.json.bak-20260721`) has planarity
  0.399 mm and tilt 0.346 deg. Worth correcting in the manuscript.

### Suggested caption

Figure N. Force-guarded bed metrology. (a) Residuals, in mm, of the nine nozzle contacts of the 3 x 3 grid
probe (21 July 2026, contacts 140 mm apart about the bed centre) from their least-squares plane; the centre
sits 0.13 mm below the plane and the peak-to-peak flatness is 0.33 mm. (b) Mean contact height per probe
session relative to the 14 July calibration plane (filled circles) and, for the sessions after the grid-fitted
plane replaced that calibration, relative to the new plane as the pre-print probe recorded it (open squares).
Whiskers span the per-point minimum to maximum; the wide grid-session whisker reflects a 0.12 degree tilt
between the stale calibration and the bed. Dashed lines mark the 0.2 mm tolerance of the pre-print gate, which
compared each probe with the height its plan had been built on, so the band shows the tolerance scale rather
than per-session gate decisions.

---

## fig_odometry.pdf (extrusion synchronisation), 3.3 x 2.35 in

### Data sources

| Quantity | Value | Source |
|---|---|---|
| Two-rectangle attempt 3, consumed / planned | 82.35 / 82.1 mm | FACT_SHEET.md section C, row 2026-07-19; primary: memory log `extrusion-scheduler-v2.md` (2026-07-19 attempt 3: "net filament 82.35mm vs ~82.1 predicted (0.3%)") |
| Attempt 5, consumed / stall marks | 562 mm / 13 | same row; memory log 2026-07-19 attempt 5 and 2026-07-20 v4 ("13 stall marks confirmed") |
| v4 consumed / stalls | 557 mm / 0 | FACT_SHEET.md row 2026-07-20 v4; memory log 2026-07-20 v4 ("zero stall re-primes", "stall marks ... eliminated") |
| v5 consumed / stalls | 573.6 mm / 0 | FACT_SHEET.md row v5; memory log 2026-07-20 v5 |
| v7 consumed / stalls | 572.1 mm / 0 | FACT_SHEET.md row v7 and table D (`square_10mm_plan_v7`); memory log 2026-07-20 v7 |
| C profile 0.5 mm bead consumed | 1006 mm | FACT_SHEET.md row 2026-07-21 C_30mm and table D (`C30_plan_v2`) |
| C profile 0.8 mm bead consumed | 1593 mm | FACT_SHEET.md row 2026-07-22 and table D (`C30_plan_w08`) |
| Planned 0.8/0.5 ratio | 1.6000 | parsed: `C30_plan_w08.json` `extrusion.params.e_per_mm` 0.099780 / `C30_plan_v2.json` `extrusion.params.e_per_mm` 0.062363 (line_width_mm 0.8 / 0.5 checked) |

The consumed and stall values are entered in the script from the fact sheet (they are not in a machine-readable
log); only the 1.60 ratio is parsed from files.

### Derivations

- Attempt 3 error: (82.35 - 82.1) / 82.1 = +0.30 %.
- Measured C scaling: 1593 / 1006 = 1.5835 (shown as x1.58). Planned scaling = e_per_mm ratio = 1.6000.
- The planned tick on the 0.8 mm C is **1.60 x 1006 = 1609.6 mm**, a ratio prediction anchored on the measured
  0.5 mm print (consumed is 1.0 % below it). It is not an absolute plan total.
- Stall panel: v4, v5 and v7 are recorded as 0 stalls / 0 stall re-primes, which is taken as 0 stall marks.
  Attempt 3 (one stall, but marks were not counted) and both C prints (stall counts 18/10,736 and about 15 were
  logged, but as stalls, not wall marks) are shown as "n/r" (not recorded).

### Not derivable / left out

- No plan-side filament total exists for attempt 5, v4, v5, v7 or the 0.5 mm C (the plan JSONs store per-waypoint
  `extrusion.flow` and `state` but no total; integrating them was not done because purge, prime and retract
  accounting would be a modelling choice). The memory log's "~expected 530s" for attempt 5 is a rough
  estimate, not a plan output, and is not plotted.
- Whether the v7 total (572.1 mm) includes its purge line is not stated in the sources.

### Suggested caption

Figure M. Filament odometry of the July 2026 prints. (a) Net filament consumed per print (dots) for the
two-rectangle test article (attempt 3: first five layers; attempt 5, v4, v5 and v7: the full 34-layer part)
and for the C profile at 0.5 mm and 0.8 mm bead width. Horizontal ticks mark a planned value where one exists:
the plan prediction for attempt 3 (82.1 mm against 82.35 mm consumed, +0.3 %), and for the 0.8 mm C print 1.60
times the filament consumed by the 0.5 mm print, the ratio of the two plans' extrusion per millimetre of path;
the measured ratio is 1.58. The other prints have no plan-side total. (b) Stall marks on the printed wall:
13 for attempt 5, none after chunk boundaries were snapped to travel moves (v4, v5, v7); n/r, not recorded.
