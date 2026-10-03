"""Runs the UNMODIFIED training/trajopt_folding.py with realistic (LuisaRender) scene export and safeguards.
Lives outside their code; nothing under code/ is edited.

  (a) uses tools/folding_render_settings.json (adds the missing "folding" scene entry; see make_folding_render_settings.py)
  (b) exports render scenes only at iterations 0, 60, 120 (their script hard-codes every 10th; each export is ~300 MB)
  (c) safeguard.py: every export wipes the whole output folder (build_luisa_script.py:629), so best_traj.npy and
      plot_data.npy are mirrored to a backup folder and restored after each export

Usage (from anywhere; needs the ThinShellLab python env, PYTHONPATH with data/AssetLoader, and `git submodule update --init`):
    export PYTHONPATH=$PYTHONPATH:$PWD/data/AssetLoader
    FOLD_L=14 python tools/run_folding_luisa.py                  # CPU, as in their script
    FOLD_L=14 TI_ARCH=cuda python tools/run_folding_luisa.py     # Taichi on the GPU (about 2x faster per iteration here)

Environment variables: FOLD_L (run id; output imgs/traj_opt_fold_<L>), FOLD_ITERS (default 121),
FOLD_KEEP (iterations to export, default "0,60,120"; must be multiples of 10), TSL_BACKUP (backup folder),
FOLD_SETTING ("folding_real" default, or "folding_2": close default camera and the blue/red "curve" paper),
FOLD_LOAD (path to a best_traj.npy to start from; with FOLD_ITERS=1 FOLD_KEEP=0 this just renders that trajectory).

folding_2 note: engine/convert_luisa.py:396 (process_curve_mix) replaces the cloth entry with a plain TextureOptions, then
convert_luisa.py:506 reads cloth_texture.both_sides, which only ClothOptions has -> AttributeError. fix_curve_mix() below wraps the
mixed texture back into a copy of the original ClothOptions.
Their scripts use relative paths, so this changes the working directory to code/.
"""
import os, runpy, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import safeguard

RUN = os.environ.get("FOLD_L", "14")
ITERS = os.environ.get("FOLD_ITERS", "121")
KEEP = {int(x) for x in os.environ.get("FOLD_KEEP", "0,60,120").split(",")}
BACKUP = os.environ.get("TSL_BACKUP", os.path.join(REPO, "imgs", "_backup", f"fold_{RUN}"))
SETTING = os.environ.get("FOLD_SETTING", "folding_real")
LOAD = os.environ.get("FOLD_LOAD")
SETTINGS = os.path.join(HERE, f"folding_render_settings_{SETTING}.json")

if not os.path.exists(SETTINGS):
    subprocess.check_call([sys.executable, os.path.join(HERE, "make_folding_render_settings.py")],
                          env=dict(os.environ, FOLD_SETTING=SETTING))

os.chdir(os.path.join(REPO, "code"))
os.makedirs(os.path.join("..", "imgs", f"traj_opt_fold_{RUN}"), exist_ok=True)  # LuisaScript mode does not create it
sys.argv = ["training/trajopt_folding.py", "--l", RUN, "--r", str(int(RUN) + 1), "--iter", ITERS, "--tot_step", "50",
            "--lr", "0.00003", "--curve7", "1", "--curve8", "-1", "--render_option", "LuisaScript"]  # = scripts/run_trajopt_folding.sh
if LOAD:
    sys.argv += ["--load_traj", os.path.abspath(LOAD)]

import thinshelllab.engine.render_engine as RE

_init = RE.Renderer.__init__


def init(self, scene_sys, env_name, option="Taichi", config_path=None):
    _init(self, scene_sys, env_name, option, SETTINGS)


RE.Renderer.__init__ = init


def fix_curve_mix():
    import copy
    _pcm = RE.process_curve_mix

    def pcm(sys_, cloth_textures):
        before = list(cloth_textures)
        _pcm(sys_, cloth_textures)
        for i, (old, new) in enumerate(zip(before, cloth_textures)):
            if new is not old and not hasattr(new, "both_sides"):   # a bare TextureOptions came back
                wrapped = copy.copy(old)
                wrapped.texture = new                                # the mixed (curve-marked) texture
                wrapped.curve = False
                cloth_textures[i] = wrapped

    RE.process_curve_mix = pcm


if SETTING == "folding_2":
    fix_curve_mix()
safeguard.install(RE, BACKUP, KEEP)
runpy.run_path("training/trajopt_folding.py", run_name="__main__")
