"""Test for safeguard.py: reproduces ThinShellLab's folder-wiping export with a fake renderer.

    python tools/test_safeguard.py

Needs only numpy. Does not touch the repo (uses a temporary directory).
"""
import os, shutil, sys, tempfile, types
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import safeguard

T = tempfile.mkdtemp(prefix="sg_test_")
OUT, BK = f"{T}/out", f"{T}/backup"


class Renderer:  # behaves like LuisaScriptRender: export = rmtree(output dir) then recreate (build_luisa_script.py:629)
    def set_save_dir(self, d):
        self.d = d
        os.makedirs(d, exist_ok=True)

    def render(self, frame, *a, **k):
        self.rendered = getattr(self, "rendered", 0) + 1

    def end_rendering(self, it):
        shutil.rmtree(self.d)
        os.makedirs(self.d)
        open(f"{self.d}/scene_0.luisa", "w").write("x")


render_engine = types.SimpleNamespace(Renderer=Renderer)
safeguard.install(render_engine, BK, {0, 60, 120}, log=lambda *_: None)
r = Renderer()
r.set_save_dir(OUT)
ok = True
for i in range(121):
    if i % 10 == 0:                      # their script renders every 10th iteration
        r.render("0")
        for f in range(1, 4):
            r.render(str(f))
    np.save(f"{OUT}/best_traj.npy", np.full(3, float(i)))
    np.save(f"{OUT}/plot_data.npy", np.arange(i + 1))
    if i % 10 == 0:
        r.end_rendering(i)
    if i in (0, 60, 120):
        ok &= os.path.exists(f"{OUT}/best_traj.npy") and os.path.exists(f"{OUT}/plot_data.npy")
best, plot = np.load(f"{OUT}/best_traj.npy"), np.load(f"{OUT}/plot_data.npy")
ok &= best[0] == 120.0 and len(plot) == 121 and r.rendered == 12   # only iterations 0, 60, 120 are rendered
shutil.rmtree(T)
print("PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
