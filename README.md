# Data for "Virtual-twin-gated robotic fused filament fabrication on an industrial six-axis arm"

Ahmad, Bokhamseen, Mekid (KFUPM). Manuscript submitted to Virtual and Physical Prototyping.
Contact: Samir Mekid, smekid@kfupm.edu.sa

All files are the ones the manuscript's numbers were computed from. Nothing here was regenerated
for the release. Coordinates are in the UR16e base_link frame unless a file says otherwise.

## plan_schema.json
JSON Schema (draft 2020-12) of the plan contract, inferred from C30_plan_v2.json; x-length values
are those of that plan, not constraints. Field semantics are described in the manuscript's Section 5.2.

## plans/  (plan JSON: the inter-stage contract described in Section 5.2)
Each file holds the G-code points, the bed-frame mapping, the tool center point and nozzle-axis mode,
the full inverse-kinematics solution with per-waypoint residuals (ik_path.max_error_m,
mean_error_m, max_axis_error_deg, failed_count, joint_positions, nozzle_axes_world), the extrusion
schedule (extrusion.params, state[], flow[], events[]) and the purge routine.
- square_real_two_plan_v2.json: two-rectangle article, attempt 3 (Table 3)
- square_10mm_plan_v4.json, _v5.json, _v7.json: two-rectangle article, 34-layer runs (Table 3)
- disc_50mm_sim.json: 50 mm disc (Table 1)
- raft_S25_sim.json: raft + S-shaped tube (Table 1; carries the layer_height 0.001 mm defect noted in the text)
- C30_plan_v2.json: 30 mm single-wall cylinder, 0.5 mm bead (Table 1, Table 3, thermal preview figure)
- C30_plan_w08.json: the same cylinder at 0.8 mm bead (Table 1, Table 3)
- S25_plan_tilt.json: S-shaped tube with G-code-normal nozzle axes under a 50 deg cap (Table 1; tilt statistics in Section 6)
- R3020_plan_v5.json: 30 x 20 mm rectangular box (Table 1)
- final_free_form_ur16e_tilt50_v2_sim.json, final_free_form_ur16e_safe30_sim.json: freeform benchmark, simulation only (Table 1, Fig. 4 collision scan)
- corner_tour_20mm_sim.json: first-motion corner tour (Section 6.2)

## exec/  (executor-resolved trajectories for the plans that ran on the robot)
Written by print_execute.py after the chained re-solve from the live pose. They contain the joint
trajectory actually streamed; their residual fields are rebuilt by forward kinematics and are not
tracking errors (the manuscript says so in Section 6).

## bed_metrology/  (force-guarded probing, Fig. 6, Section 5.3 and 6.7)
- bed_calibration.json.bak-20260721: the original four-corner touch-off calibration
- bed_calibration_20260721.json: the nine-point re-fit that replaced it
- bed_calibration_creality_20260721_retired.json: the calibration the cylinder plan was built against
- bed_probe_20260720.json, bed_probe_5pt_20260720.json, bed_probe_9pt_20260721.json,
  bed_probe_20260721.json, bed_probe_20260722.json, bed_probe_20260723.json: probe sessions.
  Sessions after the nine-point re-fit record deltas against the re-fitted plane; the figure script
  recomputes them against the original plane as well.

## slicer_jobs/  (method4 slicer outputs, Table 2, Fig. 3)
- C30f/, S25f/, R3020f/: G-code, slicer figures and the comparison_criteria.txt report per model
- integ_check/job.json, demoS/job.json: orchestrator gate records
- method4_compare_ab.png: Python port versus MATLAB reference on the S-shaped tube

## gcode/, models/
Source G-code for the disc and the freeform benchmark; STL models (C_30mm, S_25mm, R_30_20,
disc_50mm, __25mm) with their reference-centerline CSVs where present.

## twin_model/
MuJoCo cell model (ur16e_live.xml with meshes/) and the resolved UR16e URDF. World frame = controller
base frame (base_link rotated 180 deg about z).

## figure_sources/
Scripts that produced Figs. 5, 6 and 7 (fig_probe.py, fig_odometry.py, fig_thermal.py, figstyle.py),
their notes (FIGURE_NOTES.md, FIGURE_NOTES_thermal.md) and FACT_SHEET.md, which lists every number in
the manuscript with the file it comes from.

## photos/
Photographs of the cell, the head, the cylinder print and the curved tube (Figs. 2 and 8).

## License
CC BY 4.0 (see LICENSE).

## predecessor_ur5e/ (added later): the curved-tube runs on the predecessor UR5e

Execution records of the tilted-nozzle precedent reported in the Results (the 25 mm single-wall curved tube,
printed on the cell's predecessor UR5e with the same extruder head, before the gates existed). For each run:
`*.summary.json` (program metadata, 60,000 waypoints, path length, speed 5 mm/s, and the joint watch:
status, elapsed seconds, final joint delta, extrusion flag) and `*_sim.json.gz` (the IK solution: per-waypoint
targets, joint positions, nozzle axes and residuals). `curved_tube_25mm.stl` is the model; the `*.gcode.gz`
files are the MATLAB slicer outputs that were decimated to the 60,000 waypoints (support disc included).
- method4_25mm_support60_lh02_zup24_tilt45: voxel-skeleton slicer, nozzle tilt capped at 45 deg, 62.07 m, reached in 12,841 s.
- method4_25mm_support60_lh035_zup285_RAWnormals: raw layer normals (nozzle up to 97 deg from straight down, a few waypoints past horizontal), 62.07 m, reached in 12,869 s.
- method4_25mm_support80_1layer_zup36_RAWnormals_retry: raw normals, one-layer 80 mm disc, 51.01 m, reached in 10,677 s.
- ur5e_sim_urscript (method3_support80_1layer_zup40_RAWnormals): central-path slicer, 50.27 m, reached in 10,695 s, extrusion flag false in the watch.
No filament, temperature or probe data were logged for these runs; the parts were assessed visually.

## upgraded_head_cylinders/ (added later): the two surviving parts, printed with the upgraded head

Plans and real_print logs of the 30 mm and 40 mm single-wall vase cylinders (helix, pitch 0.3 mm, 0.5 x 0.3 mm bead,
210/60 C) printed on the rebuilt cell with the MK3S head: the same arm, executor and gates as the campaign, a different
head and bed. They are reported in the paper only as an as-printed dimension on the upgraded head, not as campaign
parts. `cylinder_30mm_vase_purge_plan.json` + `real_print_cylinder30_20260906.log` (6,322 waypoints, rc 0, 609.7 mm net
filament); `cylinder_40mm_vase_purge_plan.json` + `real_print_cylinder40_20260907_first.log` (6,320 waypoints, 804.2 mm)
and `_second.log` (6,319 waypoints, 806 mm).
