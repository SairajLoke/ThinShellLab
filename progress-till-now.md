# Progress till now (ThinShellLab fork, branch `crease-test`)

Status as of 2026-10-03. Everything here was run on one RTX 4060 machine (rented, now closed) unless stated. Upstream code under `code/` is unchanged; additions are in `tools/`, `results/`, the docs, and (on this branch only) one new scene file.

## Why the strip shows two crease lines
The paper strip is 15 x 3 cells (6.7 mm each) on a **fixed grid**. A 180-degree fold has to be spread over neighbouring hinge rows, because the plastic rest angle of one edge cannot reach 180 degrees: their update rule moves the rest angle only by the excess over `k_angle` = 0.5 rad, so it saturates at pi - 0.5 = 2.64 rad (151 degrees) (`code/engine/model_fold_offset.py:176-186`). The curve in the start shape is built over 3 cells, so the fold sits on rows 7 and 8 (`init_fold(..., half_curve_num=2)`, `code/engine/model_fold_offset.py:841-865`). The blue and red marker lines in the renders are exactly these two rows (`is_upper_curve` = row 7, `is_lower_curve` = row 8, `code/task_scene/Scene_folding.py`), and the Folding-U / Folding-L tasks reward the plastic angle on one of them. After the press, the two rows carry about -81 and -85 degrees per edge, together about 166 of 180 degrees. So "two creases" is a grid effect: one physical fold shared by two hinge rows. A real fold is one line; ARCSim's adaptive mesh can make one narrow crease, and the paper's own comparison is in `difference.md`.

## What was done
| Area | What | Where |
|---|---|---|
| ARCSim | built, ran the fold scene, parameter study, docs, plots | repo `SairajLoke/arc-sim` branch `dev` |
| ThinShellLab setup | two Python environments (taichi 1.7.4 and 1.6.0), LuisaRender build, helper scripts, bug list | `fixNsetup.md`, `tools/`, `env_snapshot/` |
| Folding runs | CPU and GPU, 121 iterations; GPU 501 iterations (their script's settings) | `results/`, Hugging Face `drakedrake/ppr-sim` `tsl/` |
| Profile | per-stage timing: the linear solve is 74% of an iteration (14.0 s) | `tools/profile_folding.py`, `tools/profile_*.json` |
| Docs | `simulators.md` (crease-capable simulators), `difference.md` (ARCSim vs ThinShellLab, with paper pages and file:line) | repo root |
| Crease test | scripted press / pick / open, no learning (this branch) | `code/task_scene/Scene_crease_test.py`, `tools/crease_test.py` |

## Findings so far
1. **Optimisation does not press the fold.** 501 iterations: best reward -0.05549 at iteration 108, last -0.0613, fingertip moved about 2 mm. Likely causes in their code, not yet tested: Adam learning rate x0.9 every 10 iterations (`code/optimizer/optim.py:74-75`) and a 1 mm per step clamp (`code/agent/traj_opt_single.py:15-28`, `code/training/trajopt_folding.py:53`).
2. **Same config, different path.** Two GPU runs of the identical script agree at iteration 0 and differ after about 13 iterations (no seed is involved), yet reach the same best reward.
3. **Speed.** 1506 unknowns, 49 steps x about 11.7 Newton iterations per rollout; the linear solve is cupy sparse QR (not Cholesky as their paper says) rebuilt from a dense field each call, and about half of the matrix is empty rows from fixed vertices (`code/engine/sparse_solver.py:85-103`, `code/engine/BaseScene.py:400-405`). Nothing is optimised yet.
4. **The press makes a crease.** In the scripted test a plate presses the strip to 1.4 mm above the bottom layer; per-edge plastic rest angles on the two crease rows reach about -62 / -53 degrees (pressed) and -81 / -85 degrees (plate lifted), max one edge 143 degrees. The paper then stays folded flat.
5. **Opening erases most of it, in their model.** Their yield rule keeps each rest angle within +-0.5 rad (28.6 degrees) of the current angle, so forcing the strip flat leaves only about that much per edge (rows 7 / 8 around -13 / +19 degrees after opening); what remains after release varies between runs.

## Crease test (this branch): how it works and where it stands
- Scene: the Folding scene with the fingertip starting away from the paper, plus a frozen 60 x 60 x 10 mm plate moved by script. Gravity stays off as in Folding (`code/task_scene/Scene_folding.py:30`; their sheet density is 40 per area, about 400x real paper, a possible reason, not tested). Folding has no sheet-to-sheet contact, so the press stops 1.4 mm above the bottom layer (the layers cannot be pushed through each other by contact).
- Script phases: settle, plate down, hold, plate away, fingertip to the free end, **attached grip** (that row of vertices follows the fingertip; no friction pick), swing the flap over to flat, release, settle. Only one end is lifted: the far end of the bottom layer stays fixed.
- Videos on Hugging Face (`tsl/crease_test/`): `v1_press.mp4` (first run), `v2_press.mp4`, `v2_nopress.mp4`. They show the press and the pick-up and opening working.
- **Known flaws in the first run (v1):** (a) the swing ended 4 mm short, so the opened strip was compressed and sprang up like a buckled column on release; (b) no damping, so the "settled" opening angle was a snapshot of an oscillation (148 degrees in one run, 172 in another); (c) near the fold the paper dipped 5-6 mm below the table top while opening (`k_contact` 1e5 gave NaN, 1e6 pushed 4 mm through during the press, sheet friction 0.1 gave NaN).
- **Version 2** changed (a) and (b) in the script: 2 mm of slack at the end of the swing, sheet velocity damping (x0.97 per step, 150 steps) after release, opening angle averaged over the last 20 steps. Press run and control (open without pressing), single runs: the table penetration (c) did not occur (lowest paper point 0.1 to -0.6 mm; probably because the strip is no longer compressed, not isolated), the settled angle is stable (press 155.1 degrees, range 154.6-155.4; control 145.4, range 145.1-145.7). Per-edge rest angles on rows 7 / 8: press -62 / -53 (pressed), -81 / -85 (plate lifted), then +10 / +2 after opening and release; control -16 / -19 throughout (the start shape already has about -19 from `init_ref_angle`). So in this model pressing makes a crease but forcing the strip flat undoes it, and the control keeps more bend (145 degrees) than the pressed strip (155 degrees). Videos: `v2_press.mp4`, `v2_nopress.mp4` on Hugging Face.
- **Why v2 still cannot show a crease that holds:** gravity is off, so the released strip does not lie flat; it takes its rest curvature in the air (press run: free end 62 mm above the table, control 43 mm). The `opening` value is only the angle between two directions, not "flat". The next version needs gravity on for the sheet, or the plate holding the opened strip flat before it is lifted; short smoke test first.
- The scene archive of v1 could not be copied off the machine (cut off), so only videos, metrics and logs are kept.

## Open items / next steps
1. Version 3 with gravity (or a hold-down) so the opened strip lies flat, then measure the crease after the release with a repeat; smoke-test short first.
2. Self-contact for the sheet (their unused `code/engine/geometry_self.py`) so the press can go fully flat.
3. Optimisation branch (separate branch, real optimisations, A100/H100 target): free-DOF compaction and Cholesky (dense GPU or cuDSS), fewer host syncs, reuse of the factorisation in the backward pass. `optimization.md` is not written yet.
4. Learning to crease (RL / trajectory optimisation) comes after the scripted test shows a crease that stays.

## Where things are
- Code: this branch; also `dev` has `tools/`, `results/`, `simulators.md`, `difference.md`.
- Results and videos: Hugging Face dataset `drakedrake/ppr-sim` (`tsl/`, including `tsl/crease_test/`).
- The rented machine used for all runs was closed on 2026-10-03; setup steps to rebuild it are in `fixNsetup.md`.
