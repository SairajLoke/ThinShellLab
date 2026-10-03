# ARCSim 0.2.1 vs ThinShellLab: how they simulate a paper fold

Side-by-side comparison of the two simulators used in this project, from their papers and their code. The same file is in both repositories.

## References used
- **FCA**: Narain, Pfaff, O'Brien, *Folding and Crumpling Adaptive Sheets*, SIGGRAPH 2013 (`arcsim-0.2.1/papers/`). ARCSim's plasticity and remeshing for stiff sheets.
- **AAR**: Narain, Samii, O'Brien, *Adaptive Anisotropic Remeshing for Cloth Simulation*, SIGGRAPH Asia 2012 (`arcsim-0.2.1/papers/`). ARCSim's base: material model, integrator, remeshing.
- **TSL**: Wang et al., *Thin-Shell Object Manipulations With Differentiable Physics Simulations*, ICLR 2024, [arXiv 2404.00451v1](https://arxiv.org/abs/2404.00451).
- **ARCSim code** is version 0.2.1 as in [SairajLoke/arc-sim](https://github.com/SairajLoke/arc-sim) (`src/` unchanged except a typo fix in `src/sparse.hpp`). Paths start with `src/` or `conf/`.
- **ThinShellLab code** is upstream commit `a1cf8d0` ([Genesis-Embodied-AI/ThinShellLab](https://github.com/Genesis-Embodied-AI/ThinShellLab/tree/a1cf8d0), same as `main` of [SairajLoke/ThinShellLab](https://github.com/SairajLoke/ThinShellLab)). Paths start with `code/`.

How references are written: `p.N` is the PDF page. None of the papers has line numbers, so the section, equation, figure or table is given instead. Code references are `file:line`. "Folding" means ThinShellLab's Folding task (`code/task_scene/Scene_folding.py`, `code/training/trajopt_folding.py`). "fold.json" means ARCSim's two-fold scene (`conf/fold.json`).

## 1. Purpose and output
| | ARCSim | ThinShellLab | References |
|---|---|---|---|
| Goal | Graphics: realistic folding, crumpling and wrinkling with sharp creases | Robot learning: a differentiable simulator plus benchmark tasks for manipulating thin shells | FCA p.1 abstract; TSL p.1 abstract, p.3 contributions |
| What drives the sheet | Scripted pins and kinematic obstacles (rollers) | A deformable fingertip whose rigid base follows an optimised trajectory | `conf/fold.json:23-63`; TSL p.5 §3.4, §4.1 |
| Differentiable | No | Yes: analytic gradients through the implicit step, including the plastic rest angles | TSL p.5 §3.3, p.13 A.2, p.15 A.4.4; `code/engine/analytic_grad_single.py:217-256` |
| Output | Mesh per frame (`NNNN_00.obj`) and an OpenGL viewer; paper images rendered with Mitsuba | Rewards, trajectory (`best_traj.npy`), Taichi preview or LuisaRender scenes | FCA p.7 acknowledgments; TSL p.16 A.5; `code/training/trajopt_folding.py:122-125` |

## 2. Discretisation
| | ARCSim | ThinShellLab | References |
|---|---|---|---|
| Mesh | Triangles in 2D material space plus 3D world positions; **adaptive, anisotropic remeshing** once per frame (split, flip, collapse) | **Fixed** regular triangle grid; never remeshed | AAR p.3 §3, p.3-4 §4.1; FCA p.2 Alg. 1; `src/simulation.cpp:134-137`; `code/engine/model_fold_offset.py:929` (`init_mesh`) |
| Resolution in the fold scenes | Letter sheet 216 x 279 mm, starting from 8 triangles; 3.67k faces on average in the paper's two-fold example; about 10-11k faces at t = 8 s in our runs | Strip 100 x 20 mm, 15 x 3 cells (dx = 6.7 mm): 64 vertices, 90 triangles | FCA p.7 Table 1; `conf/fold.json:8`; `plots/analysis_9runs.json`; `code/task_scene/Scene_folding.py:43-44`, `code/engine/model_fold_offset.py:13-19` |
| Why that matters for creases | Mesh edges align with the fold, which avoids bending "locking" with stiff in-plane material; fine elements only where creases form | A crease can only be a straight row of fixed grid edges; the crease width is at least one cell (6.7 mm). In Folding it is placed in advance on rows 7 and 8 | FCA p.1-2 §1 and Fig. 2; `code/task_scene/Scene_folding.py:134-143` (reward rows) |
| Volumetric bodies | None; obstacles are rigid meshes moved kinematically | Tetrahedral FEM bodies (fingertip, blocks) coupled two-way with the sheet | AAR p.3 §3; TSL p.4 §3.1; `code/engine/model_elastic_tactile.py` |

## 3. Material model of the sheet
| | ARCSim | ThinShellLab | References |
|---|---|---|---|
| In-plane (stretching) | Green strain with **measured, piecewise-linear anisotropic** stiffness tables (Wang et al. 2011); `paper.json`: E h = 0.5 MN/m | Two quadratic penalties: on edge length (`Kl`) and on triangle area (`Ka`), both 1000; isotropic, no measured data | AAR p.3 §3; FCA p.2 §3; `src/physics.cpp:68-79`, `src/dde.cpp:87`; `materials/paper.json:1-6`; TSL p.14 A.4.3 (`Use`, `Usa`); `code/engine/model_fold_offset.py:37-38, 150-167` |
| Bending | Discrete hinge (Bridson 2003 / Grinspun 2003) with measured stiffness; energy `ke * l^2/(2A) * (theta - theta_ideal)^2 / 4`, scaled by edge length and area | Discrete hinge, `Kb * (theta - ref)^2 * dx^2 / 3` with the **same weight on every edge** (a code comment says the paper's `\|e\|/\|h_e\|` weight still needs to be done); `Kb` = 400 in Folding | AAR p.3 §3; `src/physics.cpp:113-128`; TSL p.14 A.4.3 (`Ub`), p.16 Table 3; `code/engine/model_fold_offset.py:109-124`; `code/training/trajopt_folding.py:50` |
| Mass | Lumped, 1/3 of the incident material-space areas x area density (0.1 kg/m^2) | `rho * dx^2` per vertex, `rho` = 40 in Folding | AAR p.3 §3; `materials/paper.json:6`; `code/engine/model_fold_offset.py:32`; `code/task_scene/Scene_folding.py:62` |
| Strain limiting | Available (AAR's augmented-Lagrangian method); turned off in fold.json | None | AAR p.6-7 §5; `conf/fold.json:66` |

## 4. Plasticity (how a crease is made permanent)
| | ARCSim | ThinShellLab | References |
|---|---|---|---|
| Plastic variable | 2x2 **plastic bending-strain tensor `Sp` per face**; edge rest angles `theta_ideal` are derived from it (3x3 solve per face, averaged per edge) | **Scalar rest angle `ref_angle` per edge**, updated directly | FCA p.2 §3 eq. (1); `src/plasticity.cpp:199-243`; TSL p.4 §3.1; `code/engine/model_fold_offset.py:77` |
| Yield rule | Yields when the Frobenius norm of the elastic bending strain exceeds the **yield curvature kappa (1/m)**; `Sp` moves by the excess | Yields when the angle difference exceeds **`k_angle` (radians)**; `ref_angle` moves by the excess | FCA p.2 eq. (2); `src/plasticity.cpp:65-80`; TSL p.4 §3.1; `code/engine/model_fold_offset.py:176-186` |
| Yield value in the fold scenes | `yield_curv` 200 /m | `k_angle` 0.5 rad (other scenes 3.14, which means off); with dx = 6.7 mm this is roughly 75 /m, using the approximation angle ≈ curvature x edge spacing | `conf/fold.json:13`; `code/task_scene/Scene_folding.py:31`, `code/engine/model_fold_offset.py:79` |
| Mesh dependence of the yield | Curvature-based, so it does not depend on element size | Angle-based, so the same `k_angle` means a different yield curvature at a different grid spacing | FCA p.2 eq. (1)-(2); `code/engine/model_fold_offset.py:183` |
| Damage / weakening | Damage `alpha` grows when yielding (eq. 3); bending and stretching stiffness are scaled by `1/(1 + weakening * damage)`; sharper creases (FCA Fig. 3) | None (a `stiff_loss` line exists but is commented out) | FCA p.2 eq. (3), p.3 Fig. 3; `src/plasticity.cpp:79`, `src/physics.cpp:74-75, 124-126`; `code/engine/model_fold_offset.py:186` |
| Keeping the crease through remeshing | Plastic embedding (one Newton step per time step, stretching stiffness x 1e-2) plus resampling of the residual strain onto new faces | Not needed (the mesh is fixed) | FCA p.3 §3; `src/plasticity.cpp:113-119, 181-196, 253-292` |
| When it is applied | Every time step, after the implicit solve, then the embedding update | Every time step, after the Newton solve (`timestep_finish`); also once at start, so the pre-curved strip begins partly set | FCA p.2 Alg. 1; `src/simulation.cpp:131, 193-200`; `code/task_scene/Scene_folding.py:226-231`; `code/engine/model_fold_offset.py:788-797` |
| Gradient through plasticity | n/a | Yes: dL/d(ref_angle) is passed back through time | TSL p.13 A.2; `code/engine/BaseScene.py:1532-1540`; `code/engine/analytic_grad_single.py:228-229, 248` |

## 5. Time integration and solver
| | ARCSim | ThinShellLab | References |
|---|---|---|---|
| Step size in the fold scenes | 1 ms (`frame_time` 0.04 s / `frame_steps` 40); remeshing every 40 steps | 5 ms; 49 steps, so 0.245 s of motion per rollout | FCA p.2 §3 ("on the order of 1 ms"); `conf/fold.json:4-6`; TSL p.16 B.1; `code/task_scene/Scene_folding.py:35` |
| Integrator | Implicit (backward) Euler **linearised once**: one linear solve per step for the velocity change (Baraff-Witkin style) | Implicit Euler as an optimisation problem, solved by **full Newton with backtracking line search until converged** (`delta < 1e-7`, up to 1000 iterations; about 11.7 per step in our profile) | `src/physics.cpp:365-395`; TSL p.12 A.1; `code/engine/BaseScene.py:1327-1372, 1159-1197` |
| Hessian / stiffness matrix | Assembled with the forces each step; not projected | Assembled each Newton iteration; element blocks projected to positive definite (QR iteration in Taichi), contact blocks via SVD | `src/physics.cpp:241-287`; TSL p.20-21 E; `code/engine/linalg.py:6-15, 133`, `code/engine/BaseScene.py:568` |
| Linear solver | TAUCS sparse Cholesky, CPU | Paper: cuSPARSE Cholesky on the GPU. **Code: cupy `spsolve` (cuSOLVER sparse QR), rebuilt from a dense n x n Taichi field each call**; 74% of an iteration in our profile | AAR p.3 §3, FCA p.6 §5; `src/physics.cpp:387`; TSL p.21 E; `code/engine/sparse_solver.py:78-98`; `tools/profile_cuda.json` (fork) |
| Fixed / driven vertices | **Soft**: stiff springs (`handle_stiffness` 1e4 in fold.json) that fade in and out | **Hard**: the vertex's rows and columns are left out of the Newton system (zero) | `src/handle.cpp:42-53`; `conf/fold.json:67`; TSL p.5 §3.4, p.12 A.1; `code/engine/BaseScene.py:400-405` |
| Extra stabilisers | Pop filter after remeshing: minimises energy plus a fit to the pre-remesh accelerations, with regularisation `mu` = 1e3 and 10 Newton iterations | None needed (no remeshing) | FCA p.4-5 §4.3 eq. (11)-(13); `src/popfilter.cpp:76-81`; `src/simulation.cpp:312-317` |
| Parallelism, hardware | C++, OpenMP on the CPU | Taichi kernels on the CPU or GPU (their script uses `ti.cpu`); Python loop around the Newton iterations | `Makefile:12` (`-fopenmp`); TSL p.4 §3; `code/training/trajopt_folding.py:28` |

## 6. Contact and friction
| | ARCSim | ThinShellLab | References |
|---|---|---|---|
| Detection | Bounding-volume hierarchy; proximity search within 2 x `repulsion_thickness`; **continuous** collision detection for impacts | Spatial hash grid (cell 3 mm), point-to-triangle projection at the start of each step; **no continuous detection** | AAR p.3 §3; `src/proximity.cpp:62`, `src/collision.cpp:204-260`; TSL p.4 §3.2, p.13 A.3; `code/engine/geometry.py:8-16, 90-107` |
| Response | Repulsion springs (cubic energy inside `repulsion_thickness` = 1 mm, stiffness `collision_stiffness` 1e11 x area), then **non-rigid impact zones** solved as a constrained projection (up to 100 iterations) | **Quadratic penalty energy** `kr/2 * max(eps - d, 0)^2` inside the Newton solve (`kr` = 1e4, `eps` = 0.4 mm in Folding); the contact normal is kept fixed while in contact to stop vertices crossing to the other side | FCA p.2 §3; `src/constraint.cpp:59-101`, `src/collision.cpp:40, 101-140`; TSL p.5 eq. in §3.2, p.13 A.3; `code/engine/BaseScene.py:488-520, 779-817`; `code/task_scene/Scene_folding.py:46-47` |
| Friction | Coulomb friction added to the implicit step, coefficients 0.6 (cloth) and 0.3 (obstacles) by default | IPC's smooth friction potential `mu * lambda * f0(eps_v, \|u\|)`, `lambda` from the last step; `mu` = 5.0 between sheet and fingertip in Folding | `src/constraint.cpp:104-131`, `src/conf.cpp:112-113`; TSL p.5 §3.2, p.13-14 A.4.1, p.16 Table 3; `code/training/trajopt_folding.py:66` |
| Self-contact of the sheet | Yes (needed for a fold to lie on itself) | Pairs are built between sheet and bodies only in Folding (`contact_analysis`); the sheet does not collide with itself there | `src/collision.cpp:194, 204-216`; `code/task_scene/Scene_folding.py:99-108` |

## 7. Manipulator and control
| | ARCSim | ThinShellLab | References |
|---|---|---|---|
| Manipulator | Rigid kinematic obstacles (cylinder rollers, a floor plane) that cannot be pushed back by the sheet | Soft FEM fingertip (276 vertices, Stable Neo-Hookean `J - alpha` form) whose bottom and inner ring follow a 6-DoF rigid base | `conf/fold.json:52-63`; TSL p.4 §3.1, p.14 A.4.2; `code/engine/model_elastic_tactile.py:14-15, 184-201`; `code/task_scene/Scene_folding.py:111-127` |
| How motion is specified | Keyframed `motions` (translations and velocities over time), assigned to obstacles and pinned nodes | A trajectory of per-step pose increments, optimised: Adam on analytic gradients (their script) or CMA-ES / RL | `conf/fold.json:23-51`; TSL p.5 §4.1, p.17 B.3; `code/training/trajopt_folding.py:88-97, 132-138` |
| Limits on motion | None besides the script | 1 mm per step (`fix_action`, `max_moving_dist` 0.001); Adam learning rate x 0.9 every 10 iterations. The paper says the gradient method uses a soft loss on action speed; the code clamps instead | TSL p.16 B.1; `code/agent/traj_opt_single.py:15-28`; `code/optimizer/optim.py:54-75`; `code/training/trajopt_folding.py:53, 138` |
| What counts as a good fold | Visual: the shape and the plastic rest angles in the output meshes | Reward = sum of `ref_angle` on the upper crease row minus the lower row (Folding-U) | TSL p.16 B.2; `code/task_scene/Scene_folding.py:130-143` |

## 8. Speed (as reported and as measured here)
| | ARCSim | ThinShellLab | References |
|---|---|---|---|
| Reported in the paper | Two-fold example: 3.67k faces, 22.8 s per frame (integration 9.4, plasticity 7.3, collision 4.3, remeshing 0.14, projection 1.7) | Forming task, 1698 DoF: forward 36.41 s and backward 4.67 s per 100 steps on an RTX 4090 | FCA p.7 Table 1; TSL p.21 E |
| Measured here | `original_params` fold.json run: 3653 s for 350 frames (14 s simulated), about 10.4 s per frame on an i9-14900KF | Folding, 1506 DoF: 14.0 s per optimisation iteration (49 forward steps plus backward) with Taichi on an RTX 4060; 23.0 s on the CPU backend; linear solve 10.4 s of the 14.0 | `plots/runs/original_params/timing` (arc-sim); `tools/profile_cuda.json`, `tools/profile_cpu.json` (ThinShellLab fork) |

## 9. Where the papers and the code disagree (ThinShellLab)
- **Linear solver.** The paper (p.21 E) says Cholesky through cuSPARSE. The code uses cupy `spsolve`, which is sparse QR, with no factor reuse (`code/engine/sparse_solver.py:96-103`).
- **Bending weight.** The paper uses `|e|/|h_e|` per edge (p.14 A.4.3). The code uses a constant `dx^2/3`, and a comment says this still needs to be changed (`code/engine/model_fold_offset.py:120-124`).
- **Action limit.** The paper says the gradient method uses a soft loss on action speed (p.16 B.1). The code clamps the step with `fix_action` (`code/training/trajopt_folding.py:138`).
- **Elastic model of the static box.** It uses classic `log J` Neo-Hookean (`code/engine/model_elastic_offset.py:328-330`), with `nu` = 0. The fingertip uses the `J - alpha` form described in the paper. In Folding the box is fully fixed, so this does not change the result.

## 10. What each one is missing for robot paper folding (summary)
- **ARCSim:**
  - It is not differentiable.
  - Its manipulators are scripted and rigid, with no force back from the sheet.
  - It runs on the CPU only.
  - Identical configs gave different end states on two machines.
  - `resume` does not continue faithfully (6-digit output, re-anchored pins).
  - In fold.json the second fold springs back.
  - Its strengths: true crease formation anywhere, through adaptive remeshing, curvature-based yield and damage.
- **ThinShellLab:**
  - Creases can only form on a fixed grid, and in Folding the crease rows are chosen in advance.
  - The yield is angle-based (depends on mesh spacing) and there is no damage.
  - The mesh is coarse (6.7 mm cells) and there is no self-contact in Folding.
  - Its strengths: differentiable, two-way contact with a soft fingertip, GPU kernels, and a task/reward setup for learning.
  - In our runs the optimised fingertip moved only about 2 mm and the fold was not pressed.
