# results/: lightweight results from the ThinShellLab runs

Videos, rewards, best trajectories, plots and logs (3.6 MB total). The large scene/mesh archives and full outputs are in the
Hugging Face dataset `drakedrake/ppr-sim` (public), folder `tsl/`. How the runs were done: `../tools/README.md` and `../fixNsetup.md`.
Reward is "higher is better"; Folding and Pick-Folding rewards are on different scales. All runs: RTX 4060 machine, code at commit `a1cf8d0`, unmodified.

| Folder | What | Notes |
|---|---|---|
| `folding_cpu_16iters_stopped` | Folding, CPU, stopped at 16 of 400 iterations | plain Taichi preview renderer |
| `folding_cpu_121iters` | Folding, CPU, 121 iterations, LuisaRender video | best reward -0.0364 at iteration 19. **`best_traj.npy` was lost** (the render export wipes the output folder, see fixNsetup T11); rewards recovered from the log |
| `folding_gpu_121iters` | same scene, Taichi on the GPU (`TI_ARCH=cuda`) | best reward -0.0555 at iteration 109; about 15.5 s/iteration vs about 22.7 s on the CPU |
| `folding_gpu_reference_look` | the GPU run's `best_traj.npy` re-rendered with the `folding_2` look (close camera, blue/red crease lines) | video only; scenes are in the dataset |
| `pick_fold_33iters_stopped` | Pick-Folding, stopped by hand at iteration 33 of 121 | reward gained about 1%; `video_iteration0.mp4` is the untrained iteration-0 trajectory (fingertips do not move) |
| `folding_gpu_500iters_lr3e-5_kangle0.5` | Folding, GPU backend, 501 iterations with their script's settings (lr 3e-5; `k_angle` 0.5, so crease plasticity is on), `folding_2` look | best reward -0.05549 at iteration 108, last -0.0613; no gain after about iteration 110. `video_final_iter500.mp4` is the last trajectory, `video_best_iter108.mp4` the best one, re-simulated from `best_traj.npy` (reward reproduced to 3e-11). 2 h 16 min in total (16.2 s per iteration, 15.0 s of it the forward simulation). Same config as `folding_gpu_121iters`: identical at iteration 0 (to 1e-9), different trajectories after about 13 iterations, same best reward |
| `lifting_gpu_16iters_stopped`, `lifting_gpu_50iters` | Lifting on the GPU backend (the only script that initialises Taichi on the GPU) | 50-iteration reward was erratic: best -0.0205 at iteration 38, last -0.0399 |

No trained trajectory presses the fold yet: the GPU Folding trajectory moves the fingertip only about 2 mm in total, also after 500 iterations.
Likely reasons in their code (not yet tested): `Adam_single` multiplies the learning rate by 0.9 every 10 iterations (`code/optimizer/optim.py`), and
`agent_trajopt.fix_action` limits the fingertip to 1 mm per step (`max_moving_dist=0.001` in `code/training/trajopt_folding.py`).
