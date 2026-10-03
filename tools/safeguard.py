"""Protects results from ThinShellLab's LuisaScript export, which rmtree's the whole output directory
(build_luisa_script.py:629). Lives OUTSIDE the repo; used by the wrapper scripts.

 1. every np.save of best_traj.npy / plot_data.npy is mirrored immediately into BACKUP_DIR
 2. after each render export, any file missing from the output dir is restored from BACKUP_DIR
"""
import os, shutil
import numpy as np

PROTECTED = ("best_traj.npy", "plot_data.npy")


def install(render_engine, backup_dir, keep_iters, log=print):
    os.makedirs(backup_dir, exist_ok=True)
    _save = np.save

    def save(file, arr, *a, **k):
        _save(file, arr, *a, **k)
        b = os.path.basename(str(file))
        if b in PROTECTED:
            _save(os.path.join(backup_dir, b), arr)

    np.save = save

    R = render_engine.Renderer
    _set, _render, _end = R.set_save_dir, R.render, R.end_rendering
    state = {"k": -1, "on": False, "dir": None}

    def set_save_dir(self, d):
        state["dir"] = d
        return _set(self, d)

    def render(self, frame, *a, **k):
        if frame == "0":
            state["k"] += 1
            state["on"] = (state["k"] * 10) in keep_iters
        if state["on"]:
            return _render(self, frame, *a, **k)

    def end_rendering(self, it):
        if it in keep_iters:
            r = _end(self, it)
            d = state["dir"]
            os.makedirs(d, exist_ok=True)
            for b in PROTECTED:
                src = os.path.join(backup_dir, b)
                if os.path.exists(src) and not os.path.exists(os.path.join(d, b)):
                    shutil.copy(src, os.path.join(d, b))
                    log(f"[safeguard] restored {b} after export at iteration {it}")
            return r

    R.set_save_dir, R.render, R.end_rendering = set_save_dir, render, end_rendering
    return state
