# Fact sheet for the VPP manuscript (scope: the July to August 2026 campaign, as in the SII draft)

Scope decision (user, 2026-10-07): the journal paper is the SII 2027 draft expanded to journal depth.
The September and October 2026 campaigns (curve tube, maple tree, cubes, elbow infill specimens) are
OUT of this paper. The hardware swap of 2026-08-16 is mentioned only as a limitation/outlook.
Every number below traces to a repo file (inventory of 2026-08-11, re-checked paths on 2026-10-07).

## A. Hardware and cell as tested (July 2026)
- Arm: Universal Robots UR16e, 16 kg payload, PolyScope 5.21.2, RTDE at 10.89.27.227 (HANDOFF_2026-07-14.md).
- Head: Creality Ender-class direct-drive extruder + hotend with fan shroud, Marlin-class control board, mounted on a printed flange adapter (photos: user chat 2026-08-15, never uploaded; mesh mujoco/ur16e/meshes/extruder_tool0.obj).
- Print-head computer: NVIDIA Jetson, single owner of the printer serial port, exposes extrusion UDP :9410, runs its own Wi-Fi AP printer_jetson 10.42.0.1/24 (jetson/sync_loop.py, memory jetson-hotspot-topology).
- Bed: glass plate on a stand, 297.4 x 302.5 mm as calibrated 2026-07-14, surface z 93.2 to 95.1 mm in base_link, planarity residual 0.399 mm, tilt 0.346 deg (original 07-14 calibration, bed_calibration.json.bak-20260721; the 0.173 mm / 0.328 deg values belong to the 07-21 9-point re-fit, corrected 2026-10-07).
- Camera gateway: Orbbec Femto Bolt HTTP gateway (then on a Windows host at .234:8095, since moved to the Jetson .253:8095; the paper should say "depth-camera HTTP gateway" only).
- Control host: DGX Spark, aarch64, Ubuntu 24.04, Python 3.12, no ROS (CLAUDE.md).
- Post-campaign change (limitation only): 2026-08-16 extruder, hotend and bed replaced by Prusa MK3S extruder/hotend + MK52 bed, Einsy board on the Jetson USB (HANDOFF_2026-08-16.md).

## B. Pipeline stages and tools (as of the campaign)
- Slicer: method4_slicer (Python port of MATLAB method_4_05.m): voxelize STL, 3-D thinning skeleton (Lee 94), smoothing, end-axis fit, orthogonal slice planes, plane-mesh slicing, G-code with XYZ + IJK tool axis. Validation vs MATLAB ground truth: first contour point reproduced exactly (X37.5662 Y51.2853); nearest-point A to B median 0.17 mm, mean 0.34 mm, max 12.71 mm (method4_slicer/method4_compare_ab.png, method4_slicer/README.md).
- Slicer metrics per model (jobs/*/…_comparison_criteria.txt): C_30mm: toolpath gen 10.32 s (11.51 s total), 15,733.9 mm / 52,772 pts, 168 slices, avg dev 0.0102 mm, max 0.428 mm, 0 jumps > 0.6 mm. S_25mm: 11.68 s (13.84 s total), 26,261.2 mm / 88,047 pts, 338 slices, avg dev 0.767 mm, max 3.144 mm. R_30_20: avg 0.004 mm, max 0.35 mm. __25mm: avg 0.54 mm, max 2.79 mm.
- IK oracle: tools/prepare_ur5e_gcode_sim.py: G-code to bed-frame targets, greedy damped least-squares IK over the calibrated URDF chain, insert_travel_lifts(), height-law tilt caps (allowed tilt <= min(D, asin(h/R))), purge generation, extrusion scheduling. Single-branch greedy: claim empirical feasibility, never completeness (docs/PIPELINE_DESIGN.md).
- Plan JSON contract fields: gcode{points, path_length_mm, bounds}, mapping, tcp{offset, axis mode, tilt-cap summary, clamped count}, ik_path{max_error_m, mean_error_m, max_axis_error_deg, failed_count}, extrusion{params, state[], flow[], corner_deg[], events[]}, purge.
- Guards: tools/motion_guards.py (UR16e joint limits elbow +-pi others +-2pi, rebranch_within_limits, densify_fk_tips 15 substeps, assert_z_floor); tools/plan_guards.py (joint-limit margin >= 10 deg, arm-bed >= 3 mm, head-bed >= 0.2 mm, head-arm >= 5 mm, temporal head-vs-printed-part scan with bead_r 0.5 mm and active-wall exclusion recency 120 wp + tip_excl 15 mm; verdict PRINTABLE). tools/arm_bed_collision.printed_part_scan: cKDTree k-NN, ~17 s over 75k waypoints.
- Executor: tools/print_execute.py: single chained solve of approach + print + retract from the live pose, set_tcp + FK-vs-RTDE cross-check before motion, hard abort on > 20 deg consecutive joint jump, swept-tip z-floor, interpreter-mode streaming in ~450-statement chunks with snapped_chunk_bounds() onto travel waypoints then layer seams, RTDE-arrival-gated approach, dry-run re-solves the path +5 mm in air, motion needs --execute --confirm PRINT-RUN. Follows per-waypoint nozzle axes when tcp.target_axis_mode = gcode_normals, else constant straight-down (see G for what ran on hardware).
- Interpreter facts: ~450 to 500 statement drain + clear per chunk (docs/COMMUNICATION_AND_RESUME_OPTIONS.md, HANDOFF_2026-07-16.md).
- Extrusion: plan-JSON schedule + tools/extrusion_bridge.py (software pressure advance) + jetson/sync_loop.py (HEAT, ARMED, PRINTING, STOP; UDP :9410, proto-2 at 20 Hz with eseq-deduped retract/prime; dead-man staleness retract fired 0.52 s after a SIGKILL test; cooldown.py escape hatch). Params used on every printed plan: line width 0.5 mm (0.8 for the wide C), layer 0.3 mm, filament 1.75 mm, pa_k 0.04 s, retract 2.0 mm @ 40 mm/s, prime_extra 0.15, prime_lead 3.0 mm, coast 0.4 mm^3, corner_angle 35 deg, corner_stop 80 deg, e_per_mm 0.0624 (0.0998 at 0.8 mm). Purge line 80 mm, 108 points, bed side x = 140 mm.
- Bed metrology: tools/bed_calibrate.py (4-corner freedrive touch-off) and tools/bed_probe.py (force-guarded, e-Series F/T, moveUntilContact, zeroFtSensor mandatory because the wrong pendant payload gave ~73 N idle bias).
- MuJoCo twin: mujoco/ur16e/build_model.py from URDF + bed_calibration.json, world frame = controller base frame (base_link rotated 180 deg about Z); flange FK equals RTDE getActualTCPPose to 0.0 mm (HANDOFF_2026-07-14.md); live_viewer.py :8097 (MJPEG, plan overlay by extrusion state, F/T strip charts), preview_traj.py :8098, path_overlay.py.
- Thermal twin (built 2026-08-09/10, twin/): contact-graph FEM, one lumped element per deposited segment, FV conductances (axial, lateral, interlayer, bed), convection + linearized radiation, two-branch cp(T), explicit Euler dt 10 ms auto-clamped, 65 to 100x real time for 10k elements on one ARM core; bond index from Wool-O'Connor / Yang-Pitchumani healing with PLA WLF/VFT (Dorgan) + Pokluda neck growth. Validated on C30_plan_v2.json: 10,625 elements, 167 layers, 21,027 edges, graph build 0.12 s, T_peak median 206.4 C. Uncalibrated tw_ref, bond is a relative index; live mode never saw a print. Citations in twin/RESEARCH_LOG.md.
- GUI (gui/, :8099): STL upload, drag placement on the calibrated bed, Slice & Check, IK + guards, PRINTABLE/NOT with mapped toolpath, Play in MuJoCo. Result: normal-following FAILED arm-bed (-6.4 mm) where straight-down PASSED (+8.9 mm) for the same part. S_25mm upright at bed center: PRINTABLE, 50 slices, IK max err 0.005 mm, 0 failed, joint margin 72 deg.
- Telegram bot (telegram/, stdlib long polling): /status /temps /snap /slice /preview /run /abort; motion fenced 5 ways (config flag, execute_user_ids allowlist, 5-min single-user CONFIRM, atomic executor slot, delegation to the gated executor); /abort and /status bypass the worker pool; selftest.py --all without a token. Latencies: /status 0.4 s, /snap 2.2 to 2.4 s, /vision 33.4 s (telegram/bot.log).
- Self-test pattern: every downstream dependency verifiable headlessly (telegram/selftest.py; all pipeline stages are file-to-file).

**Part names (verified from STLs 2026-10-07):** C_30mm = closed single-wall CYLINDER, 30 mm diameter x 50 mm tall (not a C-profile); S_25mm = S-shaped tube 25 x 34 x 97.5 mm; R_30_20 = 30 x 20 mm rectangular box; disc_50mm = 50 mm disc.

Additional dated facts (memory extrusion-scheduler-v2 log, CLAUDE.md): 2026-07-19 attempt 4 aborted at about waypoint 2,000 after a ur_rtde receive drop served a frozen pose ("plastic not flowing"); attempts 1 and 2 ended before a complete first layer and were not instrumented; the Telegram bot was completed 2026-07-26, after the last campaign print (07-23). Slicer metrics R_30_20 (jobs/R3020f/R3020f_comparison_criteria.txt): toolpath gen 10.89 s (11.63 s total), 16,562.9 mm / 55,610 pts, 168 slices, 0 jumps > 0.6 mm (max jump 0.30 mm); __25mm has no criteria file.

## C. Hardware execution timeline (HANDOFF_2026-07-14/16.md, memory extrusion-scheduler-v2, ur16e-first-motion)
| Date | Event | Numbers |
|---|---|---|
| 2026-07-14 | First commanded motion: bed-perimeter corner tour at bed + 20 mm | 73 movej waypoints, 54 s, ended 20.4 mm above corner BL with 0.1 mm horizontal error, safety NORMAL |
| 2026-07-14 | Bed recalibration, 4-corner touch-off | 297.4 x 302.5 mm, center [0.498, -0.268, 0.095] m, planarity residual 0.399 mm, tilt 0.346 deg (07-14 original) |
| 2026-07-14 | Nozzle-into-bed incident (dry run, S_25mm) | approach and print chains on different wrist branches (135.6 deg wrist-2 seam); movej interpolation swept the nozzle to -47 mm through the bed plane; fixes: single chained solve, hard > 20 deg jump abort, sweep check every hop |
| 2026-07-15 | Freeform transfer UR5e to UR16e (final_free_form.gcode: 74,806 moves, 87.4 m, 50 x 101 x 185 mm, normals to 118 deg tilt) | IK 3 to 5 um, 0 failures; two whole-path PRINTABLE plans: safe30 (36 % tilt kept, arm +10.1 mm, head +0.45 mm) and tilt50 (58 % tilt kept, arm +10.3 mm, head +0.44 mm); temporal scan ~12 % of waypoints within 0.5 mm of an older feature, worst -0.48 mm skim at wp 69,730; never executed (executor straight-down only) |
| 2026-07-16 | First real PLA: 50 mm disc, then raft + S (Round 4) | ~4,500 waypoints continuous speed-synced extrusion at 15 mm/s, 210/60 C, halted by a since-fixed watchdog bug; first-layer lesson: 0.35 mm plowed (79 mm filament, nothing stuck) so >= 0.5 mm required given +-0.4 mm planarity |
| 2026-07-19 | Two-rectangle 10 mm article, attempts 1 to 5 | att.3 first plan-aware print (5 layers, 19/19 retract/prime events, net filament 82.35 mm vs 82.1 predicted = 0.3 % error); att.5 full part, 34 layers, 21.3 min, rc=0, survived 2 RTDE outages (1.1 s, 1.4 s) + 13 micro-stalls, 562 mm filament, 13 stall marks on the wall |
| 2026-07-20 | v4 (chunk boundaries snapped to travels) | 34 layers, 21.4 min, rc=0, 0 stalls, 0 outages, 557 mm; 22/22 boundaries snapped, stall marks gone |
| 2026-07-20 | v5 (seam relocation + prime lead) | 21.2 min, rc=0, 0 stalls, 573.6 mm |
| 2026-07-20 | Force-guarded probing live | bed +1.30 mm vs 07-14 cal, spread 0.15 mm, tilt 35 mdeg, recommendation 1.551 mm (hand-tuned 1.5 within 0.05 mm); contact 1.8 to 5.1 N peak; idle |F| bias ~73 N from wrong payload, zeroFtSensor() mandatory |
| 2026-07-20 | v7 "everything print" (purge + seam + probed z) | complete, 572.1 mm net, 0 stalls/outages, 9,311/9,311 waypoints tracked |
| 2026-07-21 | 9-point grid cal; R_30_20 and S_25mm attempts | 9-pt: mean delta +1.52 mm vs the 07-14 plane (center point +1.39 mm), 119 mdeg mis-tilt, central dip -0.13 mm, residual peak-to-peak 0.33 mm (bed_probe_9pt_20260721.json); probe repeatability 27 um is from the session log only (no JSON records it); first live probe-gate refusal (local spot -0.33 mm below global plane); R died at 20 mm height, S at 29 %, both from filament ground flat at the drive gear |
| 2026-07-21 | C_30mm COMPLETE, first full STL through the whole pipeline (probe gate, heat, side purge, print) | 10,736 waypoints, 18.3 min, rc=0, 1006 mm filament, 50 mm tall; stall rate 18/10,736 (C) and 5/2,750 (S) vs ~1/180 before |
| 2026-07-22 | C reprint, 0.8 mm bead, seam-snapped | COMPLETE, 18.3 min, rc=0, 1593 mm filament = 1.6x the 0.5 mm C (flow scaling: measured ratio 1593/1006 = 1.58 against the commanded 1.60 = 0.0998/0.0624 e_per_mm); "1 boundary to travels, 13 to layer seams" |
| 2026-07-22 | 0.8 mm C reprint #2 | FAILED at 26 % (13/50 mm): 0.8 x 0.3 @ 15 mm/s = 3.6 mm^3/s exceeds hotend melt rate; rule <= ~2.5 mm^3/s at 210 C |
| 2026-07-22/23 | Program mode (tools/program_print_execute.py, monolithic URScript over 30002) | offline parity: joint trajectories bit-identical to print_execute, same gate verdicts; 10.7k lines / 1.03 MB; never live-tested |
| 2026-07-23 | Heater cartridge intermittent | Marlin "Heating failed E0", plateaus 157, 144.7, 150 C; heat gate refused cleanly twice; probe z drift -0.089 to -0.283 mm across the session, flatness 0.016 mm |
| 2026-08-09 | Cell down | extruder board unplugged, UR16e powered down, Jetson AP wedged after 39 d (rtl8822ce), clock 96 days behind |

## D. Plan metrics (plan/exec JSONs at repo root; exec files carry NO independent tracking error)
| Plan | Geometry | G-code pts | Path (m) | IK waypoints | IK max err (um) | mean (um) | max axis err (deg) | failed | Hardware |
|---|---|---|---|---|---|---|---|---|---|
| square_10mm_plan_v7 | two 10 mm rectangles, purge + seam, probed z 1.551 | 6,092 | 13.00 | 9,312 | 3.09 | 0.039 | 0.00096 | 0 | complete, 34 layers, 572.1 mm, 0 stalls |
| disc_50mm_sim | 50 mm disc, gcode_normals axis (all vertical, tilt 0.0 deg) | 33,400 | 40.02 | 33,400 | 2.88 | 0.019 | 0.0033 | 0 | complete (first PLA) |
| raft_S25_sim | 50 mm raft + S_25mm to 97.8 mm | 91,387 | 30.46 | 91,496 | 2.90 | 0.007 | 0.0033 | 0 | partial (~4,500 wp); layer_height_mm = 0.001 bug in this plan |
| C30_plan_v2 | C_30mm, 0.5 mm bead; target_axis_mode gcode_normals but the source normals are all vertical (tilt 0.0 deg) | 10,524 | 15.73 | 10,737 | 9.74 | 0.054 | 0.0028 | 0 | COMPLETE 18.3 min, 1006 mm |
| C30_plan_w08 | C_30mm, 0.8 mm bead | 10,524 | 15.73 | 10,737 | 9.74 | 0.054 | 0.0028 | 0 | #1 complete 1593 mm; #2 failed at 26 % |
| S25_plan_tilt | S_25mm 97.5 mm, axis = G-code normals under a 50 deg cap, 6,580 wp clamped near the bed; source normals tilt max 26.5 deg, median 11.7 deg; EXECUTED portion (first 29 %) had nozzle tilt max 8.2 deg, median 3.6 deg, 34 % of waypoints > 5 deg (computed 2026-10-07 from ik_path.nozzle_axes_world) | 17,616 | 26.27 | 17,897 | 9.80 | 0.048 | 0.0028 | 0 | died at 29 % (ground filament), i.e. mildly tilted axes DID run on hardware |
| R3020_plan_v5 | R_30_20 box 50 mm | 11,079 | 16.39 | 11,298 | 9.81 | 0.047 | 0.0028 | 0 | died at 20 mm (ground filament) |
| final_free_form_ur16e_tilt50_v2_sim | freeform 185 mm | 74,806 | 87.4 | 74,806 | <= 5 | | | 0 | simulation only |
- Gate records with JSON: jobs/integ_check/job.json (2026-07-16): 50 slices, 2,040 points, IK 3.07 um, 0 failed, TCP round-trip max_pos_err 0.0 m, max_axis_err 2.5e-16; stage timings S1 4.50 s, S3 2.23 s, TCP inject 0.037 s. jobs/demoS/job.json similar. Other GUI jobs persisted no verdict (stdout only).

## E. Bed metrology series (repo root JSONs)
- bed_calibration.json: the 07-21 9-point RE-FIT (not the 07-14 original): 297.4 x 302.5 mm, center [0.498, -0.268, 0.0955] m, planarity residual 0.173 mm, tilt 0.328 deg, embedded 3 x 3 probe flatness_pp 0.328 mm. Original 07-14 values (bed_calibration.json.bak-20260721): planarity 0.399 mm, tilt 0.346 deg.
- bed_probe_20260720.json: single point, delta +1.316 mm vs old cal, 8.9 N, force_limit contact.
- bed_probe_5pt_20260720.json: 5-pt, bed uniformly +1.30 mm, spread 0.15 mm, tilt 35 mdeg, recommendation 1.551 mm.
- bed_probe_9pt_20260721.json + bed_calibration_20260721.json: 9-pt grid, mean delta +1.52 mm vs 07-14 (center +1.39 mm), 119 mdeg mis-tilt, central dip -0.13 mm, residual peak-to-peak 0.33 mm; repeatability 27 um from the session log.
- bed_probe_20260721.json / _20260722.json: 5-pt pre-print gates, measured against the 07-21 9-point plane (their old_bed_calibration block still says created 07-14, but origin/normal are the re-fit): recorded means -0.37 and -0.43 mm; against the 07-14 plane these are +1.15 and +1.09 mm. Drift 0.2 to 0.24 mm vs the 0.2 mm tolerance; refusals became routine (no JSON records a verdict; verdicts live in the session log).
- bed_probe_20260723.json: 5 points all ok; per-point delta -0.472 to -0.599 mm, mean_delta -0.533 mm MEASURED AGAINST THE 07-21 9-POINT PLANE (against the 07-14 plane it is +0.99 mm), flatness_pp 0.0164 mm (best recorded), tilt 111 mdeg, recommended z translate -0.283 mm; contact 1.5 to 3.3 N (peaks 2.0 to 5.0 N).

## F. Figure candidates (existing files)
- figs/f1_architecture.pdf (authored TikZ dataflow; source figs/f1_architecture.tex).
- figs/f4_printcollide.jpg = gui/static/printcollide.jpg: temporal collision check at freeform wp 69,730 (worst flagged skim), two views.
- figs/f5_printed_part.jpg: curved tubular part on raft, UR5e-era print of the freeform geometry (user-supplied; identity per user, caption as in SII draft).
- method4_slicer/method4_compare_ab.png: slicer validation A/B vs MATLAB (1920 x 720).
- jobs/C30f/C30f_fig1_overview.png (mesh + toolpath + centerline), C30f_fig3_frames.png, S25f_fig2_centerline_vs_desired.png, *_fig25_skeleton.png (slicer stages).
- mujoco/ur16e/pose_iso.png etc.: bare-arm twin renders (user rejected as a figure: bed floats, no head). A mid-print twin render script exists in the session scratchpad (render_f2.py) but the bed-floating objection stands.
- gui/static/freeform_diag.jpg, head_candidates.jpg, mount_check.jpg, tip_check.jpg: head mount / TCP diagnostics.
- docs/preview_gui_screenshot.png: older Tk preview GUI (empty state).
- To generate (data exists): bed probe residual map / drift series plot from bed_probe_*.json; filament predicted vs consumed chart (82.35/82.1, 562, 557, 573.6, 572.1, 1006, 1593); stall-rate before/after boundary snapping; thermal twin bead temperature render (twin server :8102 screenshot, needs the service running).
- Missing: photos of the UR16e cell and of the July printed parts with scale (never uploaded); the Ender-head close-ups exist only in chat.

## G. Caveats that bound the claims
- No RTDE joint-tracking error was recorded; exec JSONs rebuild max_error_m = 0.0 by FK. Claim only simulated IK residuals and filament odometry.
- No dimensional metrology of the July parts (no photos, no calipers in repo).
- Nozzle tilt on hardware (resolved 2026-10-07 from plan files + tools/print_execute.py, which follows per-waypoint axes when tcp.target_axis_mode = gcode_normals): the completed cylinder and the disc had vertical axes (0 deg); the S-tube run executed mildly tilted axes (max 8.2 deg over the printed 29 %); strongly tilted plans (freeform benchmark, requested up to 118 deg, capped at 50 deg) were cleared in simulation only. The HANDOFF_2026-08-09 line "tilted-nozzle printing never ran on hardware" is true only for the strongly tilted freeform plan. Program mode never live; the plan-driven extrusion schedule, the 20 Hz event protocol and the on-head v2 sync loop DID run on hardware from 2026-07-19 (19/19 retract/prime events, memory extrusion-scheduler-v2 campaign log); not done: hardware tuning of the pressure-advance gain (K = 0.04 s used as-is) and of the melt lag; thermal twin live mode never saw a print.
- print_job.py G3 IK gate was soft; raft plan carried the layer_height 0.001 mm bug; gate thresholds duplicated across files (arm-bed 3 mm vs 15 mm in corner-tour tools).
- Repo had no git during the campaign; provenance is file mtimes + handoffs + memory logs.
