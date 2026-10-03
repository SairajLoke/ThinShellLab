#!/bin/bash
# Python environments used for the experiments (Ubuntu 24.04, uv, Python 3.9, CUDA 12.x).
#   bash tools/setup_env.sh          run from the repo root
# env1 (taichi 1.7.4): Folding, Lifting. env2 (taichi 1.6.0): Pick-Folding only.
# Pick-Folding fails to compile under taichi 1.7.3 / 1.7.4 (LLVM "Instruction does not dominate all uses!" on both
# CPU and CUDA backends), and compiles under 1.6.0.
# The full pinned package lists are in tools/requirements_env1_taichi1.7.4.txt and tools/requirements_env2_taichi1.6.0_pickfold.txt.
set -ex
REPO=$PWD
git submodule update --init --recursive        # data/AssetLoader (render_engine.py imports it unconditionally); ~1.3 GB

make_env () {   # $1 = env dir, $2 = taichi version
  uv venv --python 3.9 "$1"
  . "$1/bin/activate"
  uv pip install torch --index-url https://download.pytorch.org/whl/cu124
  # deviations from pyproject.toml: cupy-cuda12x (prebuilt) instead of cupy; numpy<2 (their code uses np.product);
  # opencv-python==4.10.0.84 (5.x requires numpy 2)
  uv pip install "taichi==$2" cupy-cuda12x cma gymnasium h5py imageio matplotlib "numpy<2" open3d \
      "opencv-python==4.10.0.84" Pillow sb3_contrib stable_baselines3 trimesh
  uv pip install -e "$REPO" --no-deps
  deactivate
}
make_env "$REPO/../venv_tsl" 1.7.4
make_env "$REPO/../venv_tsl2" 1.6.0
echo "done. Use:  export PYTHONPATH=\$PYTHONPATH:$REPO/data/AssetLoader"
