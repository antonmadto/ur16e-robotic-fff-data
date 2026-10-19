# Figure notes: thermal twin preview of C30_plan_v2 (fig_thermal)

Generated 2026-10-07, offline, file to file on the DGX. No server was started or restarted,
ports 8097 to 8103 were not touched, and neither the robot nor the Jetson was contacted.

## Files

| File | What |
|---|---|
| `figs/fig_thermal.pdf` | The requested figure: (a) peak temperature per bead, (b) per-layer relative bond index |
| `figs/fig_thermal_contact.pdf` | Recommended alternative, same twin run: (a) substrate temperature at contact, (b) critical weld time |
| `figs/src/fig_thermal.py` | The only script. It runs the twin through its Python API and draws both figures |

Both PDFs are 6.5 x 2.06 in, STIX serif (Times-like, matching the `interact` class), all fonts
embedded (TrueType), no in-figure title, and the dense bead map in (a) is rasterised at 600 dpi.

## The part is a cylinder, not a C profile

`C30_plan_v2.json` comes from `models/C_30mm.stl` through `jobs/C30f/C30f_1p5.gcode`. In the twin
the part elements lie at radius 14.8 to 15.1 mm about one axis: it is a **30 mm diameter, 50 mm tall
single-wall cylinder** (0.5 mm bead, 0.3 mm layers, 63 bead elements per layer), the part printed
complete on 2026-07-21 in 18.3 min. A plain x or y versus z side view would lay the back wall exactly
behind the front wall and hide half the beads, so panel (a) of `fig_thermal.pdf` uses the
**developed (unrolled) wall** instead: horizontal axis = arc length around the cylinder (0 to 94.2 mm),
vertical axis = height above the first layer, one rectangle per bead element (its arc from start to
end point, one layer high), centred on the element centroid. The layer-change seam falls at the
right edge (88 to 94 mm), which is why that edge is ragged: coasting and travel there deposit no
element.

## Commands and API calls

```bash
cd ~/isaac_ws && . .venv/bin/activate && export MPLBACKEND=Agg
# heavy work ran with the cache in the session scratchpad:
python paper/vpp2026/figs/src/fig_thermal.py --variant both \
    --cache /tmp/claude-1000/-home-edge-ur-fdm-cnc-isaac-ws/a53d8478-7433-46f5-9f78-71aaa431b200/scratchpad/fig_thermal_cache.npz \
    --recompute
# preview / legibility check
pdftoppm -png -r 200 paper/vpp2026/figs/fig_thermal.pdf         <scratch>/final_spec
pdftoppm -png -r 200 paper/vpp2026/figs/fig_thermal_contact.pdf <scratch>/final_contact
```

Without `--cache` the script simply reruns the twin (about 40 s). With an existing cache and no
`--recompute` it only redraws. `--variant spec|contact|both` picks the output.

Twin API used (inside `compute()` in the script):

1. `cfg = twin.thermal_fem.TwinConfig.load()`: reads `twin/twin_config.json` unchanged (PLA,
   T_nozzle 210 C, dep_offset 3 C so T_dep = 207 C, T_bed 60 C, T_amb 30 C manual, h_conv 12,
   h_c interlayer/lateral/bed 500/300/1000 W/m2K, radiation on, dt 0.01 s, **tw_ref 0.02 s**).
2. `plan = load_plan("C30_plan_v2.json")`.
3. `g = ThermalGraph(plan, cfg, bed_cal)` with `bed_cal` = `bed_calibration_creality_20260721_retired.json`
   (see the next section).
4. `sim = ThermalSim(g, cfg)`, then `while sim.t < g.print_time + 30.0: sim.step()`. This is exactly
   the loop of `twin.thermal_fem.run_headless` (replay at plan timing, 30 s cool-down tail).
5. Read `sim.T_peak` (per-element peak temperature) and `sim.element_bond(relative=True)`
   (per-element relative bond index).
6. A second identical run with `cfg.tw_ref = 0.1` for the sensitivity curve.
7. For the alternative figure, the first run also records two diagnostics per step through the public
   state only (the twin code is not modified): the substrate temperature at contact (the lower
   element's temperature in the step in which its interface to the new bead becomes alive) and the
   uncapped healing integral `H = sum dt / a_T(T_int)` over steps with T_int > Tg, using
   `twin.bond_model.shift_factor` and the same `T_int = (T_lower + T_upper)/2` the twin uses. Check:
   `min(1, (H / 0.1)**0.25)` reproduces the twin's own D_h of the tw_ref = 0.1 run to 3e-15.

## Bed calibration choice (why 167 layers)

The twin assigns layers along the bed-plane normal. With the calibration the plan was built against
and that was live at the 2026-08-09 validation (`bed_calibration_creality_20260721_retired.json`, the
Creality bed), the graph reproduces the fact sheet exactly: **10,625 elements, 167 layers,
21,027 edges** (10,404 interlayer interfaces). `python -m twin.thermal_fem C30_plan_v2.json` today
reads the current `bed_calibration.json` (MK52 bed, 2026-09-16) and gives 168 layers and
21,028 edges for the same plan; with no calibration it gives 168 layers and 21,026 edges.

## Run time

Full replay, every element deposited (10,625 of 10,625): 1,100.5 s simulated (1,070.5 s plan print
time + 30 s tail), 110,050 explicit Euler steps at dt = 10 ms (stability limit 0.43 s).

| Step | Wall time |
|---|---|
| Graph build | 0.13 s |
| Replay, tw_ref 0.02 s, with the two diagnostics | 20.8 s |
| Replay, tw_ref 0.1 s | 18.2 s |
| Whole script (both runs + both figures) | 40.0 s |

A plain replay without diagnostics took 17.2 s = 64x real time on one ARM core (RESEARCH_LOG: 64 to 70x).

## Numbers (check against FACT_SHEET.md line 28)

| Quantity | Value |
|---|---|
| Elements / layers / edges / interlayer interfaces | 10,625 / 167 / 21,027 / 10,404 (fact sheet: 10,625 / 167 / 21,027) |
| Purge-line elements (inside the plan's purge box, excluded from map only) | 105 (part: 10,520) |
| T_peak median, all elements | **206.43 C** (fact sheet 206.4 C), part only also 206.43 C |
| T_peak range, part | 205.78 to 206.80 C (T_dep = 207 C) |
| B_rel at tw_ref 0.02 s | 1.000 at every element with an interface below (min = median = 1.0) |
| B_rel at tw_ref 0.1 s | layer 1 median 0.859 (min 0.803); every other layer median 1.0; none below the 0.6 weak flag |
| Substrate T at contact, median | layer 1: 58.3 C, layer 2: 94.7 C, layer 3: 101.0 C, layer 8: 106.6 C, steady (layers 21+): 107.0 C; overall range 58.3 to 201.6 C (the maximum is at the layer-change seam) |
| Critical weld time t_w*, median | layer 1: 0.054 s (min 0.041 s), layer 2: 0.276 s, steady: 0.454 s; minimum over layers >= 2: 0.16 s |

## Quantities plotted and how they are derived

**fig_thermal.pdf (as requested)**

- (a) Per-element peak temperature `sim.T_peak` (C) on the developed wall, purge line excluded.
  Colour: ColorBrewer YlOrRd truncated to 0.22 to 1.0 (semantic heat ramp; OKLab lightness falls
  monotonically from about 0.91 to 0.40, so it reads in grayscale and under colour-vision deficiency),
  colour limits 205.7 to 206.9 C.
  **Read this panel with care: it is nearly constant by construction.** A bead enters the model at
  T_dep = 207 C (initial condition) and only cools afterwards; reheating by the next layer can never
  exceed T_dep. The recorded peak is the value after the bead's first 10 ms step, so the whole 1 C
  spread is first-step cooling into the neighbours: the first layer (on the 60 C bed) is lowest,
  and the darker rows about every 6 mm are the meshing artefact described below.
- (b) Per-layer median (line) and interquartile range (band) of `sim.element_bond(relative=True)`
  over the elements of each layer, for tw_ref = 0.02 s (default, blue solid) and 0.1 s (upper end of
  the plausible range 1e-3 to 1e-1 s quoted in `thermal_fem.py`, orange dashed). Per-element value =
  the worst interface to the layer below (the twin's display convention); layer 0 has no interface
  below and is not plotted, so the axis runs 1 to 166. B_rel = min(1, D_ic x D_h / D_ic_nom), with
  D_h the reptation healing degree and D_ic the Pokluda contact degree normalised by its nominal
  squeeze-seeded value. Log layer axis so that the bed-affected first layers are visible. Grey line =
  the GUI weak-bond flag 0.6. At the default the bond index is saturated (1.0 everywhere) and the
  IQR bands have zero width; only the 0.1 s curve departs, at layer 1.

**fig_thermal_contact.pdf (recommended alternative)**

- (a) Substrate temperature at contact: per interface, the lower bead's temperature just before the
  new bead lands; per element the minimum over its interfaces; per layer median (line) and IQR (band).
  Grey line = Tg = 60 C.
- (b) Critical weld time t_w* = H = integral of dt / a_T(T_int) over the time T_int > Tg (WLF/VFT shift
  factor referenced to 180 C, Dorgan constants), per element the minimum over its interfaces, per
  layer median and IQR, log axes. Since chi = H / tw_ref and D_h = min(1, chi^0.25), an interface heals
  fully (B_rel = 1) exactly when tw_ref <= t_w* (to within 0.6 %, the D_ic seed margin). Grey band =
  plausible tw_ref range 1e-3 to 1e-1 s; dark line = default 0.02 s.

Colours: series slot 1 `#2a78d6` and slot 2 `#eb6834` from the dataviz reference palette; the pair
passes the validator (CVD dE 24.7, normal-vision dE 33.6, contrast >= 3:1). The two series in
`fig_thermal.pdf` (b) also differ by line style (solid vs dashed) so they separate in grayscale; the
grayscale render was checked.

## Why the alternative is recommended

Both requested quantities are close to degenerate for this plan. Peak temperature only restates the
deposition temperature (a 1 C spread produced in the first 10 ms), and the relative bond index is
saturated at 1.0 at the default calibration. The alternative shows what actually discriminates in
the twin for this part: the bed-cooled start (layer 1 lands on a first layer held at 58 C, the
substrate reaches a steady 107 C by layer 8) and how much margin each layer's healing has against the
one uncalibrated knob. Its message, in one line: at the default tw_ref every interface heals fully;
the first interlayer interface is the only one whose verdict depends on calibration (it flips once
tw_ref exceeds 0.041 to 0.054 s, minimum to median of that layer); every interface from layer 2 up keeps full healing over the whole plausible
range (t_w* >= 0.16 s > 0.1 s).

## Meshing artefact (affects both figures, worth a sentence in the text)

Every 20 to 21 layers (layers 1, 21, 42, 62, 82/83, 93, 114, 134, 154) the slicer's layer start shifts
along the path, so the segment midpoints of successive layers are offset by about 0.3 mm **along**
the bead instead of being stacked (normal offset 0.002 mm). `ThermalGraph` uses the midpoint
distance as a **lateral** overlap proxy (`ov = 1 - dxy / w`), so the interlayer conductance of those
layers drops to 0.13 to 0.71 of the nominal value. The layer above then lands on a hotter substrate:
the spikes in `fig_thermal_contact.pdf` (layers 22, 43, 63, 84, 94, 115, 135, 155, up to +15 C) and
the darker rows in `fig_thermal.pdf` (a) (+0.2 to 0.4 C). It is not physics. **Layer 1 is itself one
of the offset layers** (conductance 0.40 of nominal), so the one discriminating bond number (layer 1)
carries this artefact too. A fix (overlap from the along-path and cross-path offset separately) belongs
in `twin/thermal_fem.py` and was not attempted here.

## Caveats (state in the caption or text)

- The thermal model is **uncalibrated**: h_conv, the contact conductances and tw_ref are literature
  values; the calibration protocol in `twin/RESEARCH_LOG.md` (cooling tail, reheat spike, first-layer
  cooling, z-tensile bars) has not been run. Claim trends, not absolute temperatures.
- The bond index is **relative** (1 = as healed as this bead geometry allows), never a strength in MPa.
- Replay timing is the plan at constant print (15 mm/s) and travel (30 mm/s) speed, without
  acceleration or chunk pauses: 17.8 min replay vs the 18.3 min actual print.
- Ambient 30 C is a manual value (no ambient sensor in the cell). The plan dates from the Creality
  bed and E3D-style head of July 2026; the twin's live mode has never seen a print.

## Suggested captions

**For fig_thermal.pdf (as requested):**

Thermal digital-twin preview of the C_30mm plan (30 mm diameter, 50 mm tall single-wall cylinder,
0.5 mm bead, 0.3 mm layers; 10,625 bead elements in 167 layers, 21,027 contact-graph edges), replayed
offline at plan timing. (a) Developed view of the cylinder wall, one rectangle per bead element at its
centroid, coloured by its peak temperature: every bead peaks within 1.3 C of the 207 C deposition
temperature (median 206.4 C). (b) Per-layer median of the relative interlayer bond index (band:
interquartile range) for the default reference weld time t_w,ref = 0.02 s and for the upper end of
its plausible range, 0.1 s. The model is uncalibrated and the bond index is relative (1 = fully
healed for this bead geometry), not a strength.

**For fig_thermal_contact.pdf (recommended):**

Thermal digital-twin preview of the C_30mm plan (30 mm diameter, 50 mm tall single-wall cylinder;
10,625 bead elements in 167 layers), replayed offline at plan timing. (a) Temperature of the
substrate bead when the next bead lands (median per layer, band: interquartile range): layer 1 lands
on a first layer held near the 60 C bed (58 C), and the substrate settles at 107 C from layer 8.
(b) Critical weld time t_w*, the largest reference weld time at which an interface still heals fully.
Every interface exceeds the default 0.02 s, so the twin predicts full healing everywhere; only the
first interlayer interface (0.054 s) falls inside the plausible but uncalibrated range of 0.001 to
0.1 s. The periodic spikes are a contact-graph artefact where the layer start shifts along the path.
The model is uncalibrated: trends, not absolute values.
