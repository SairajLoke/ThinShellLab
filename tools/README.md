# tools/: running and rendering ThinShellLab experiments without editing `code/`

Scripts added next to the repo, not inside `code/`. Nothing under `code/` or `data/` was changed. They were used to run the Folding and
Pick-Folding trajectory-optimisation tasks with the realistic (LuisaRender) renderer. Results of those runs, with configs, are in the
Hugging Face dataset `drakedrake/ppr-sim` (`tsl/`).

| File | What it does |
|---|---|
| `setup_env.sh` | Two Python 3.9 environments: taichi 1.7.4 (Folding, Lifting) and taichi 1.6.0 (Pick-Folding). Pinned lists: `requirements_env*.txt`. |
| `setup_luisarender.sh` | Builds LuisaRender (CUDA backend) at the pinned commit. |
| `make_folding_render_settings.py` | Writes `folding_render_settings.json`: the repo's settings plus the missing `folding` entry. |
| `run_folding_luisa.py` | Runs the unmodified `training/trajopt_folding.py` with LuisaScript export, limited to iterations 0/60/120, with the safeguard. |
| `safeguard.py`, `test_safeguard.py` | Protects `best_traj.npy` / `plot_data.npy` from the export that deletes the output folder (see below). Test: `python tools/test_safeguard.py`. |
| `render_scenes.sh`, `exr_to_png.py` | Renders the exported `scene_*.luisa` files with `luisa-render-cli` and makes an mp4. |

## Order
```
bash tools/setup_env.sh && bash tools/setup_luisarender.sh
export PYTHONPATH=$PYTHONPATH:$PWD/data/AssetLoader
FOLD_L=14 TI_ARCH=cuda python tools/run_folding_luisa.py          # drop TI_ARCH to run on the CPU as their script does
tools/render_scenes.sh imgs/traj_opt_fold_14 fold14               # needs ffmpeg, opencv; LUISA_BIN if not in ~/LuisaRender
```
Pick-Folding (run inside the taichi 1.6.0 environment, folder must exist first):
```
mkdir -p imgs/traj_opt_pick_fold_6; cd code
python training/trajopt_pick_fold.py --l 6 --r 7 --iter 121 --render 60 --tot_step 50 --lr 0.00001 --render_option LuisaScript
```
Pick-Folding has no safeguard wrapper yet, so the same folder wipe applies at every export (iterations 0, 60, ... with `--render 60`).
The one run that was done was stopped at iteration 33 and had exported only at iteration 0, before any result files were saved.

## Problems found in this repo version (and what the scripts do about them)
1. **`shutil.rmtree(self.script_dir)` in `engine/build_luisa_script.py:629`** runs on every render export, deleting the whole output folder including
   `best_traj.npy` and `plot_data.npy`. One run lost `best_traj.npy` this way. `safeguard.py` mirrors those files on every save and restores them after
   each export.
2. **No `folding` entry in `data/scene_texture_options.json`**; `folding_2` crashes (`'TextureOptions' object has no attribute 'both_sides'`,
   `engine/convert_luisa.py:506`) and `folding_real` crashes (`KeyError: 'pure_1_solid'`, `engine/render_engine.py:121`; that preset is not defined).
   Handled by `make_folding_render_settings.py`.
3. **LuisaScript mode does not create the output folder**; `run_folding_luisa.py` creates it. For Pick-Folding create it yourself.
4. `trajopt_folding.py` hard-codes rendering every 10th iteration (about 300 MB per export); the wrapper keeps only 0/60/120.
5. `training/trajopt_lifting.py` has a relative import that fails when run as a script; run it as `python -m thinshelllab.training.trajopt_lifting`.
6. Pick-Folding does not compile under taichi 1.7.3/1.7.4 (see `setup_env.sh`); use the 1.6.0 environment.
7. The LuisaScript render settings only exist for some scene names (`pick`, `lift`, `folding_*`, ...); Folding and Lifting use `folding` and `lifting` in code.

## Measured / not verified
- Measured on one RTX 4060 machine: Folding about 22.7 to 27 s per iteration on CPU, about 12.8 s on the GPU backend (`TI_ARCH=cuda`,
  taichi 1.7.4); a 1024 x 1024 LuisaRender frame in about 5 s including startup.
- The first reward differs between CPU (-0.1591) and GPU (-0.1455). No seed is involved (their code sets none); the cause is unverified.
- `setup_env.sh` and `setup_luisarender.sh` are written from the steps that were run by hand and were not re-run as scripts.
