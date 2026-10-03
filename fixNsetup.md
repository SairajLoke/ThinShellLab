# fixNsetup: bugs hit, what finally worked, and how to set it up again

Covers the three things that were built and run: **ARCSim 0.2.1** (C++ cloth/paper simulator), **ThinShellLab** (Taichi, differentiable thin-shell
manipulation) and **LuisaRender** (the offline path tracer used for the realistic ThinShellLab images).
Everything here comes from what was actually run in these sessions. **Not verified:** the install scripts (`tools/setup_env.sh`,
`tools/setup_luisarender.sh`) were written from the manual steps and have not been run as scripts on a fresh machine; do that first and
fix what breaks. Raw versions of everything installed are in `env_snapshot/`.

## 1. Working configuration (what produced the results)

| Component | Version / setting |
|---|---|
| Remote machine (vast.ai, non-persistent) | Ubuntu 24.04.4, kernel 6.8, i9-14900KF (32 threads), RTX 4060 8 GB, driver 570.211.01, CUDA 12.8 (nvcc), g++ 13.3, CMake 3.28.3, Ninja 1.11.1, uv 0.12.10, ffmpeg 6.1.1 |
| Laptop (ARCSim only) | Ubuntu 20.04.6, i5-1135G7, g++ 11.4, Boost 1.71, GNU Make 4.2.1 |
| ARCSim | arcsim-0.2.1 from graphics.berkeley.edu + two source changes (section 4.1), built `-O3 -fopenmp -std=gnu++14` |
| ThinShellLab | fork `SairajLoke/ThinShellLab`, commit `a1cf8d0` (code unmodified); helper scripts in `tools/` (branch `dev`) |
| ThinShellLab submodule | `data/AssetLoader` commit `32d56a2b4748eee6884b4360cacb37d6f0e66609` (about 1.3 GB) |
| Python env 1 (Folding, Lifting) | Python 3.9.25, **taichi 1.7.4**, torch 2.6.0+cu124, **numpy 1.26.4**, **opencv-python 4.10.0.84**, **cupy-cuda12x 13.6.0**, stable-baselines3 2.7.1, gymnasium 1.1.1, open3d 0.19.0 |
| Python env 2 (Pick-Folding) | same as env 1 but **taichi 1.6.0** |
| LuisaRender | `5722bc3fbe372983c0db4b292cff54b2615ead0c` (branch `next`), submodule `src/compute` `c54c86280a9fb466afac6777fc8827b08d9ebd73`, CUDA backend, GUI libs ON |

## 2. Is there a venv?

Yes, three, all on the **remote** machine (they disappear when that instance is destroyed; `env_snapshot/` is how to rebuild them):

| Path | Python | Used for | Pinned list |
|---|---|---|---|
| `/root/venv_tsl` | 3.9.25 (made with `uv venv --python 3.9`) | ThinShellLab Folding / Lifting, taichi 1.7.4 | `env_snapshot/pip_freeze_venv_tsl_taichi1.7.4.txt` |
| `/root/venv_tsl2` | 3.9.25 | ThinShellLab Pick-Folding, taichi 1.6.0 | `env_snapshot/pip_freeze_venv_tsl2_taichi1.6.0.txt` |
| `/root/venv` | 3.12.3 | rendering helpers, ARCSim video rendering (numpy, matplotlib), Hugging Face uploads | `env_snapshot/pip_freeze_venv_analysis_py3.12.txt` |

The laptop has **no project venv**: ARCSim is C++, and plotting used the system `python3` (matplotlib 3.7.3) plus a temporary `pip --target` folder
for plotly. System package lists for both machines are in `env_snapshot/remote_system.txt` and `env_snapshot/laptop_system.txt`.
(`tools/requirements_env1_taichi1.7.4.txt` and `..._env2_...pickfold.txt` are the same lists as the first two freezes.)

## 3. Setup, step by step

### 3.1 ARCSim (Ubuntu 20.04 or 24.04)
```bash
sudo apt install libblas-dev liblapack-dev libboost-all-dev freeglut3-dev gfortran libpng-dev zlib1g-dev libglu1-mesa-dev
sudo apt install libatlas-base-dev        # Ubuntu 24.04: TAUCS's example programs link -lcblas -latlas, make fails without it
cd arcsim-0.2.1/dependencies
make                                      # builds ALGLIB and TAUCS; the jsoncpp step FAILS (Python 2 SConstruct), do it by hand:
( cd jsoncpp && mkdir -p ../include/json ../lib /tmp/jo &&
  for f in json_reader json_value json_writer; do g++ -O2 -Iinclude -c src/lib_json/$f.cpp -o /tmp/jo/$f.o; done &&
  ar rcs ../lib/libjson.a /tmp/jo/*.o && cp include/json/*.h ../include/json/ )
make                                      # now finishes TAUCS; lib/ must hold libalglib.a libjson.a libtaucs.a
cd ..
# two source changes (also in the Hugging Face dataset: arcsim/_common/arcsim_changes_vs_original.patch):
#   Makefile LDFLAGS:  -lboost_*-mt  ->  -lboost_filesystem -lboost_system -lboost_thread
#   src/sparse.hpp:118  file << "}]" << file;   ->   file << "}]";
make bin/arcsim -j8 CXXFLAGS_RELEASE="-O3 -Wreturn-type -fopenmp -std=gnu++14"
bin/arcsim simulateoffline conf/fold.json outputs/fold_test        # headless; 351 frames; ~1 h on the remote
```
Check: `ls dependencies/lib` shows three `.a` files; `bin/arcsim` exists; `outputs/fold_test/0350_00.obj` exists.

### 3.2 ThinShellLab environments (remote or any Linux with an NVIDIA GPU)
```bash
git clone https://github.com/SairajLoke/ThinShellLab.git && cd ThinShellLab && git checkout dev
git submodule update --init --recursive          # data/AssetLoader (render_engine.py imports it unconditionally)
# env 1  (repeat with taichi==1.6.0 and another folder for env 2)
uv venv --python 3.9 ../venv_tsl && . ../venv_tsl/bin/activate
uv pip install torch --index-url https://download.pytorch.org/whl/cu124
uv pip install taichi==1.7.4 cupy-cuda12x cma gymnasium h5py imageio matplotlib "numpy<2" open3d \
    "opencv-python==4.10.0.84" Pillow sb3_contrib stable_baselines3 trimesh
uv pip install -e . --no-deps
export PYTHONPATH=$PYTHONPATH:$PWD/data/AssetLoader
```
To reproduce the pins exactly use `uv pip install -r env_snapshot/pip_freeze_venv_tsl_taichi1.7.4.txt --extra-index-url https://download.pytorch.org/whl/cu124 --index-strategy unsafe-best-match`
(the `--index-strategy` flag was needed: without it uv could not resolve `certifi` across the two indexes).
Check: `python -c "import torch, taichi; print(torch.cuda.is_available(), taichi.__version__)"` prints `True 1.7.4`.

### 3.3 LuisaRender (CUDA backend; needs an NVIDIA GPU with the OptiX runtime, which `NVIDIA_DRIVER_CAPABILITIES=all` provided)
```bash
bash tools/setup_luisarender.sh ~/LuisaRender      # apt packages, clone at the pinned commit, cmake (GUI ON), build with ninja (roughly 10 minutes on 32 threads here; not timed precisely)
ls ~/LuisaRender/build/bin/luisa-render-cli
```
Check: rendering one exported scene (section 3.4) prints "Rendering finished" and writes `render.exr`.

### 3.4 Running and rendering ThinShellLab (details in `tools/README.md`)
```bash
export PYTHONPATH=$PYTHONPATH:$PWD/data/AssetLoader
# Folding on the GPU backend, LuisaRender scenes exported at iterations 0/60/120, results protected against the folder wipe:
FOLD_L=14 TI_ARCH=cuda python tools/run_folding_luisa.py
# the reference look (close camera, blue/red crease lines) from an existing trajectory, 1 iteration:
FOLD_SETTING=folding_2 FOLD_L=15 FOLD_ITERS=1 FOLD_KEEP=0 FOLD_LOAD=imgs/traj_opt_fold_14/best_traj.npy TI_ARCH=cuda python tools/run_folding_luisa.py
python tools/mix_to_multiply.py imgs/traj_opt_fold_15          # needed for folding_2 (LuisaRender build has no `mix` texture)
tools/render_scenes.sh imgs/traj_opt_fold_15 fold15_ref        # needs ffmpeg and opencv in the python on PATH (OPENCV_IO_ENABLE_OPENEXR is set by exr_to_png.py)
```
Pick-Folding (env 2 / taichi 1.6.0; create the output folder first):
```bash
mkdir -p imgs/traj_opt_pick_fold_6 && cd code
python training/trajopt_pick_fold.py --l 6 --r 7 --iter 121 --render 60 --tot_step 50 --lr 0.00001 --render_option LuisaScript
```

## 4. Bugs hit, causes, and the fix that worked

### 4.1 ARCSim
| # | Symptom | Cause | Fix |
|---|---|---|---|
| A1 | `dependencies/make`: `SyntaxError: Missing parentheses in call to 'print'` in jsoncpp's `SConstruct` | SConstruct is Python 2; `scons` runs Python 3 | build the 3 jsoncpp files by hand (3.1) |
| A2 | TAUCS build ends with `cannot find -lcblas / -latlas` (Ubuntu 24.04) | example programs need ATLAS; the library itself still gets built | `apt install libatlas-base-dev`, rerun `make` |
| A3 | link error `cannot find -lboost_filesystem-mt` | Makefile uses non-Ubuntu Boost names | drop `-mt` from the three Boost libs |
| A4 | `error: no match for operator<< (std::ostream, std::fstream)` at `src/sparse.hpp:118` | typo in a debug-only function, accepted by pre-C++11 compilers | `file << "}]";` |
| A5 | `call of overloaded 'clamp(double, double, double)' is ambiguous` in `display.cpp` | g++ defaults to C++17, which has `std::clamp` next to the project's own `clamp` | add `-std=gnu++14` via `CXXFLAGS_RELEASE=...` |
| A6 | plain `make` fails at the `ctags` target | ctags not installed | `make bin/arcsim` |
| A7 | `bin/arcsim resume` does not continue a run faithfully (resumed frame jumps by mm) | frames are written with 6 significant digits; pins are re-anchored at the node's current position | use full reruns for comparisons |
| A8 | identical config on different machines ends in different states | parallel summation order / contact ordering; not a seed | compare end states statistically; repeat each setting |

### 4.2 ThinShellLab (their code was never edited)
| # | Symptom | Cause | Fix |
|---|---|---|---|
| T1 | `ModuleNotFoundError: No module named 'assets_lookup'` | `render_engine.py` imports the `AssetLoader` submodule unconditionally | `git submodule update --init --recursive`; add `data/AssetLoader` to `PYTHONPATH` |
| T2 | `AttributeError: module 'numpy' has no attribute 'product'` (`model_elastic_offset.py:27`) | removed in NumPy 2 | `numpy<2` |
| T3 | opencv-python 5.x wants numpy>=2 | version conflict with T2 | `opencv-python==4.10.0.84` |
| T4 | `pip install cupy` builds from source | no wheel for the plain name | `cupy-cuda12x` (`uv pip check` still complains that `cupy` is missing; harmless) |
| T5 | Pick-Folding: `Instruction does not dominate all uses!` + `Assertion failure: !llvm::verifyFunction` | Taichi 1.7.3 / 1.7.4 LLVM codegen bug on this scene's kernels (CPU and CUDA backends); which kernel was not identified | **taichi 1.6.0** |
| T6 | `training/trajopt_lifting.py`: `ImportError: attempted relative import with no known parent package` | script uses `from ..agent...` | run as `python -m thinshelllab.training.trajopt_lifting` |
| T7 | `--render_option LuisaScript` raises `Invalid environment name` for Folding / Lifting | the settings file has no `folding` / `lifting` entries (only `pick`, `lift`, `folding_2`, `folding_real`, ...) | settings copy with a `folding` entry (`tools/make_folding_render_settings.py`) |
| T8 | `folding_real`: `KeyError: 'pure_1_solid'` (`render_engine.py:121`) | that fingertip preset is not defined anywhere in the code | settings copy uses the existing `pure_1` |
| T9 | `folding_2`: `AttributeError: 'TextureOptions' object has no attribute 'both_sides'` (`convert_luisa.py:506`) | `process_curve_mix` (`convert_luisa.py:396`) puts a bare `TextureOptions` where a `ClothOptions` is expected | `tools/run_folding_luisa.py` wraps the result back into a copy of the original `ClothOptions` (`FOLD_SETTING=folding_2`) |
| T10 | `FileNotFoundError ... imgs/traj_opt_pick_fold_5/best_traj.npy` right after iteration 0 | LuisaScript mode does not create the output folder (Taichi mode does) | `mkdir -p` it first (the Folding wrapper does this) |
| T11 | **`best_traj.npy` and `plot_data.npy` disappear** after a render export | every export runs `shutil.rmtree(script_dir)` (`build_luisa_script.py:629`) on the whole output folder; one run lost its `best_traj.npy` this way | `tools/safeguard.py` mirrors both files at every save and restores them after each export (tested; confirmed on the real GPU run) |
| T12 | each Folding render export is about 300 MB and happens every 10 iterations | `trajopt_folding.py` hard-codes `i % 10 == 0` | wrapper exports only at the iterations in `FOLD_KEEP` (default 0, 60, 120) |
| T13 | CPU and GPU runs start from different rewards (-0.1591 vs -0.1455) | **not established**; no seed is involved (none found in the Folding path files that were checked; the initial trajectory is zeros); suspect parallel `ti.atomic_add` ordering in contact collection | open |

### 4.3 LuisaRender
| # | Symptom | Cause | Fix |
|---|---|---|---|
| L1 | build stops at `src/films/display.cpp: fatal error: imgui.h` and `luisa-render-cli` is never produced | I had set `LUISA_COMPUTE_ENABLE_GUI=OFF`; the CLI target depends on every plugin including the ImGui "display" film | `-D LUISA_COMPUTE_ENABLE_GUI=ON` |
| L2 | rendering the `folding_2` scenes segfaults | the scene uses a `mix` texture plugin that this LuisaRender source does not have (it has `multiply` with inputs `a`, `b`); log line: `Failed to load dynamic module libluisa-render-texture-mix.so` | `tools/mix_to_multiply.py` rewrites `mix { top, bottom, method "multiply" }` to `multiply { a, b }` in the exported scene files (originals kept) |
| L3 | EXR output cannot be read by OpenCV | OpenCV disables EXR by default | `OPENCV_IO_ENABLE_OPENEXR=1` before `import cv2` (done in `tools/exr_to_png.py`) |
| L4 | plugins not found at run time | shared libraries live in `build/bin` | `export LD_LIBRARY_PATH=<LuisaRender>/build/bin:$LD_LIBRARY_PATH` (done in `render_scenes.sh`) |

### 4.4 Working with the remote machine
- `ssh -f ... < file` does **not** pass stdin to the remote command (the Hugging Face token arrived empty and the upload failed). Use plain `ssh` and start the job inside it: `read -r VAR; ...; setsid nohup cmd > log 2>&1 < /dev/null &`.
- `ssh host 'pkill -f pattern'` kills its own shell when the pattern also appears in the command line; anchor it (`pkill -f "^python training/..."`).
- A backgrounded job inside an `ssh` call can hang the session; start with `setsid nohup ... < /dev/null &`, return, and check with a second `ssh`.
- `scp host:"a b"` does not work with newer OpenSSH; one `scp` per remote file.
- The login banner prints text addressed to "AI agents"; it came from the server, not from the user, and was ignored.
- The machine is rented and non-persistent: copy results off and push them (Hugging Face dataset `drakedrake/ppr-sim`, branch `dev` of the fork) before destroying it.

## 5. Open / unverified
- The install scripts in `tools/` have not been run end to end on a fresh machine.
- T13 (CPU vs GPU reward mismatch) and A8 (run-to-run divergence) are not explained.
- Folding and Pick-Folding were run for 121 and 33 iterations; their scripts default to 400. No trained trajectory presses the fold yet.
- ARCSim's results are single runs per setting; see the dataset's `arcsim/batch1_summary.md` for what the noise looked like.

## 6. Where things are
- `tools/`: wrappers, safeguard (+ test), render and setup scripts, pinned requirements.
- `env_snapshot/`: system, apt and pip snapshots of both machines and the three venvs.
- `results/`: lightweight results from the runs (videos, rewards, best trajectories, plots, logs); the large scene/mesh archives are in the dataset.
- Hugging Face dataset `drakedrake/ppr-sim` (public): `arcsim/` and `tsl/` experiments with configs, full outputs and per-run READMEs.
