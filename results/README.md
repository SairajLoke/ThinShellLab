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
| `lifting_gpu_16iters_stopped`, `lifting_gpu_50iters` | Lifting on the GPU backend (the only script that initialises Taichi on the GPU) | 50-iteration reward was erratic: best -0.0205 at iteration 38, last -0.0399 |

No trained trajectory presses the fold yet: the GPU Folding trajectory moves the fingertip only about 2 mm in total. Longer runs (their script defaults to 400 iterations) are still to do.
