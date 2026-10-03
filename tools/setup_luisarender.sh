#!/bin/bash
# Builds LuisaRender (the offline path tracer used for the realistic images) with the CUDA backend.
# Tested on Ubuntu 24.04, g++ 13.3, CMake 3.28, CUDA 12.8, RTX 4060 (driver 570). Needs an NVIDIA GPU with OptiX runtime.
#   bash tools/setup_luisarender.sh [install_dir]      (default ~/LuisaRender)
# Pinned to the versions that were used: LuisaRender 5722bc3fbe372983c0db4b292cff54b2615ead0c (branch next),
# its src/compute submodule c54c86280a9fb466afac6777fc8827b08d9ebd73.
set -ex
DIR=${1:-$HOME/LuisaRender}
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq cmake ninja-build uuid-dev libopencv-dev libglfw3-dev libxinerama-dev libxcursor-dev libxi-dev \
    libx11-dev libxrandr-dev libgl1-mesa-dev zlib1g-dev
git clone --recurse-submodules -j8 https://github.com/LuisaGroup/LuisaRender.git "$DIR"
cd "$DIR"
git checkout 5722bc3fbe372983c0db4b292cff54b2615ead0c
git submodule update --init --recursive
# GUI must stay ON: the luisa-render-cli target depends on every plugin, including the "display" film that needs ImGui
# (with LUISA_COMPUTE_ENABLE_GUI=OFF the build fails at src/films/display.cpp: imgui.h not found).
cmake -S . -B build -G Ninja -D CMAKE_BUILD_TYPE=Release -D LUISA_COMPUTE_ENABLE_CUDA=ON -D LUISA_COMPUTE_ENABLE_GUI=ON \
      -D LUISA_COMPUTE_ENABLE_DX=OFF -D LUISA_COMPUTE_ENABLE_METAL=OFF -D LUISA_COMPUTE_ENABLE_VULKAN=OFF
cmake --build build -j "$(nproc)"
ls build/bin/luisa-render-cli
