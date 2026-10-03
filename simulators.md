# Simulators that can make a paper crease

These were found while looking for a recent simulator that creases paper the way ARCSim and ThinShellLab do (a plastic fold that stays). Each entry has one comment on what it does and what it misses for robot paper folding.

How much was checked: each comment comes from the project's README, project page or paper abstract (web search, October 2026), unless it says "used here". None of the new ones was installed or run. A detailed comparison of the two simulators used here is in `difference.md`.

## Used in this project
| Simulator | What it does / what it misses | Links |
|---|---|---|
| **ARCSim 0.2.1** (Narain, Pfaff, O'Brien) | Adaptive remeshing aligns the mesh with creases. Plasticity is curvature-based with damage, so creases can form anywhere. Misses: not differentiable, CPU only, scripted rigid manipulators only, and runs are not repeatable across machines. Used here. | Paper: [Folding and Crumpling Adaptive Sheets (SIGGRAPH 2013)](https://dl.acm.org/doi/10.1145/2461912.2462010); code: [graphics.berkeley.edu/resources/ARCSim](http://graphics.berkeley.edu/resources/ARCSim/), fork used here: [SairajLoke/arc-sim](https://github.com/SairajLoke/arc-sim) |
| **ThinShellLab** (Wang et al.) | Differentiable implicit simulator (Taichi, CPU/GPU) with a per-edge plastic rest angle and a soft FEM fingertip; ships Folding and Pick-Folding tasks. Misses: fixed coarse grid, so creases only on preset grid rows; angle-based yield with no damage; slow linear solve; no trained trajectory included. Used here. | Paper: [arXiv 2404.00451 (ICLR 2024)](https://arxiv.org/abs/2404.00451); code: [Genesis-Embodied-AI/ThinShellLab](https://github.com/Genesis-Embodied-AI/ThinShellLab), fork used here: [SairajLoke/ThinShellLab](https://github.com/SairajLoke/ThinShellLab) |
| ARCSim 0.3.1 fixes | Install fixes and an installer script for a later ARCSim version (same method). Misses: everything ARCSim misses. | [kaist-silab/arcsim](https://github.com/kaist-silab/arcsim) |

## Closest new candidates
| Simulator | What it does / what it misses | Links |
|---|---|---|
| **Lightwheel simulator (Robotic Origami Challenge, IROS 2026)** | Built on NVIDIA Isaac Sim, described as "thin-shell paper physics, plastic creasing, fold memory". Includes digital twins of the Sharpa robot hands and paper-airplane task setups, which is the closest match to the end goal. Misses: only given to registered teams through a form; no public code; how creases are modelled is not described. A CC-BY-4.0 real-robot dataset (682 episodes, tactile signals, 1.91 TB) is public. | Challenge: [robotic-origami-challenge.github.io](https://robotic-origami-challenge.github.io/); dataset: [SharpaIT/Robotic_Origami_Challenge](https://huggingface.co/datasets/SharpaIT/Robotic_Origami_Challenge) |
| **Crease Lab** (lukacslacko, created Aug 2026) | XPBD paper model in the browser (CPU, plus a WebGPU option). The mesh refines where it bends sharply, like ARCSim. Hinge rest angles flow past a yield curvature, but only under fingertip pressure (crease radius about 1.5 thicknesses), and creases survive remeshing. Six scripted fingertip and pin scenarios. Misses: not differentiable (only a finite-difference check); JavaScript only; no licence, so the code cannot be reused; no papers or validation. | [github.com/lukacslacko/origami](https://github.com/lukacslacko/origami) |
| **Learnable Persistent Wrinkle Formation / Fabric-101** (Gong et al., SIGGRAPH Asia 2026) | Differentiable cloth simulator with elastic, frictional and plastic response; learns parameters from measured hysteresis curves with the adjoint method. Misses: built and measured for fabric, not paper; no manipulator tasks. | Paper: [arXiv 2609.13707](https://arxiv.org/abs/2609.13707); code: [GongDeshan/Fabric_101_for_Wrinkles](https://github.com/GongDeshan/Fabric_101_for_Wrinkles) |

## Related, but no plastic creasing found
| Simulator | What it does / what it misses | Links |
|---|---|---|
| Genesis (MPM, and FEM cloth with libuipc contact) | GPU robotics simulator. MPM paper bends into a smooth curl, not a sharp crease; the cloth + IPC prototype is for shirts. Misses: no crease plasticity for sheets found. | [Genesis IPC shirt-folding prototype](https://github.com/happy1041/genesis-ipc-shirt-demo); ThinShellLab is hosted under the same organisation |
| libuipc / StiffGIPC | GPU incremental-potential contact with a Newton solver and implicit integration; robust contact for stiff thin shells. Misses: no bending plasticity found. | [pyuipc on PyPI](https://pypi.org/project/pyuipc/); [StiffGIPC (TOG 2025)](https://dl.acm.org/doi/10.1145/3735126) |
| NVIDIA Newton (on Warp) | GPU, differentiable; has XPBD, VBD and Style3D cloth solvers. Misses: no bend plasticity or creasing found in what was searched. | [newton-physics/newton](https://github.com/newton-physics/newton) |
| Isaac Sim plastic-deformation extension | Pseudo-plastic permanent deformation for Isaac Sim's volumetric (tetrahedral FEM) deformables. Misses: volumes only, not thin sheets. | [hijimasa/isaac-sim-plastic-deformation](https://github.com/hijimasa/isaac-sim-plastic-deformation) |
| Origami Simulator (Ghassaei) | Real-time GPU (WebGL) folding of a given crease pattern by crease springs. Misses: creases fixed in advance, no plasticity, no contact with a manipulator. | [amandaghassaei/OrigamiSimulator](https://github.com/amandaghassaei/OrigamiSimulator); [paper](https://amandaghassaei.com/projects/origami_simulator/files/FastInteractiveOrigamiSimGPU.pdf) |
| From Fold to Function (MuJoCo deformables) | Origami mechanisms built from MuJoCo deformable elements with user-defined creases. Misses: creases predefined, no plastic crease formation. | [arXiv 2511.10580](https://arxiv.org/abs/2511.10580) |
| Discovering Folding Lines for Surface Compression (SIGGRAPH Asia 2025) | Uses MPM to compress a shell, then extracts straight fold lines. Misses: MPM gives smooth bends, so fold lines need post-processing; design tool, not a manipulation simulator. | [ACM DL](https://dl.acm.org/doi/full/10.1145/3757377.3763983) |

## Checked and not about creasing
| Paper | Why it is not a crease simulator | Links |
|---|---|---|
| Tactile Genesis (2026) | GPU tactile-sensor simulation at scale for dexterous learning; no paper, folding or plasticity. | [arXiv 2606.22332](https://arxiv.org/abs/2606.22332) |
| HydroShear (2026) | Hydroelastic shear model for tactile sim-to-real reinforcement learning; independent of the physics engine; no thin sheets. | [arXiv 2603.00446](https://arxiv.org/abs/2603.00446) |
