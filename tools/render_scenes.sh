#!/bin/bash
# Renders the scene_<i>.luisa files written by a LuisaScript run, then assembles a video.
#   tools/render_scenes.sh <scene_dir> <name>
# e.g. tools/render_scenes.sh imgs/traj_opt_fold_14 fold14   ->  render_out/fold14/f0000.png ... and render_out/fold14.mp4
# Env: LUISA_BIN (folder with luisa-render-cli, default ~/LuisaRender/build/bin), PYTHON (needs opencv-python+numpy),
#      RENDER_OUT (default ./render_out), FPS (default 10)
# About 2-5 s per 1024x1024 frame (256 spp) on an RTX 4060; the sheet render writes render.exr into <scene_dir>.
set -e
SCENE_DIR=$(cd "$1" && pwd); NAME=$2
LUISA_BIN=${LUISA_BIN:-$HOME/LuisaRender/build/bin}
PYTHON=${PYTHON:-python}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${RENDER_OUT:-$PWD/render_out}/$NAME
mkdir -p "$OUT"
export LD_LIBRARY_PATH=$LUISA_BIN:$LD_LIBRARY_PATH
cd "$SCENE_DIR"
n=$(ls scene_*.luisa | wc -l)
for i in $(seq 0 $((n-1))); do
  "$LUISA_BIN/luisa-render-cli" -b cuda -d 0 scene_$i.luisa > /dev/null 2>&1
  "$PYTHON" "$HERE/exr_to_png.py" render.exr "$OUT/f$(printf %04d $i).png"
done
ffmpeg -y -v error -framerate "${FPS:-10}" -i "$OUT/f%04d.png" -c:v libx264 -pix_fmt yuv420p -crf 20 "$OUT.mp4"
echo "rendered $n frames -> $OUT.mp4"
