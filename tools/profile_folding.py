"""Per-stage timing of ThinShellLab's Folding trajectory optimisation, without editing their code.

Runs the unmodified training/trajopt_folding.py for a few iterations with the Taichi preview renderer and wraps the stages of the
simulation (forward Newton solve, linear solve, line search, energy / Hessian assembly, contact) and of the backward pass with timers.
Taichi / GPU work is synchronised (ti.sync) before and after each timed call, so the numbers are wall time, not launch time.
Iteration 0 (kernel compilation) is excluded.

    python tools/profile_folding.py [ITERS=4]                    # CPU, as in their script
    TI_ARCH=cuda python tools/profile_folding.py [ITERS=4]       # Taichi on the GPU
Writes tools/profile_<arch>.json and prints a table.
Note: nested stages overlap (e.g. time_step contains newton_step contains solve); shares are of the forward+backward total.
"""
import atexit, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ITERS = sys.argv[1] if len(sys.argv) > 1 else "4"
ARCH = os.environ.get("TI_ARCH", "cpu")
os.chdir(os.path.join(REPO, "code"))
os.makedirs("../imgs/traj_opt_fold_90", exist_ok=True)
sys.argv = ["training/trajopt_folding.py", "--l", "90", "--r", "91", "--iter", ITERS, "--tot_step", "50", "--lr", "0.00003",
            "--curve7", "1", "--curve8", "-1"]

import taichi as ti

stats = {}          # name -> [seconds, calls]
state = {"iter_done": 0, "t0": None, "wall": 0.0}


def reset():
    stats.clear()
    state["t0"] = time.time()


def timed(name, fn):
    def wrapper(*a, **k):
        if state["iter_done"] < 1:           # skip the compile-heavy first iteration
            return fn(*a, **k)
        ti.sync(); t = time.time()
        r = fn(*a, **k)
        ti.sync()
        s = stats.setdefault(name, [0.0, 0])
        s[0] += time.time() - t; s[1] += 1
        return r
    return wrapper


SCENE_METHODS = ["time_step", "newton_step", "compute_residual_and_Hessian", "compute_energy", "linesearch_step", "push_down_pos",
                 "contact_analysis", "calc_vn", "timestep_init", "timestep_finish", "newton_step_init", "norm_F", "calc_p_norm", "norm_P"]
GRAD_METHODS = ["transfer_grad", "get_loss_fold", "copy_pos"]

def install(Scene, Grad):
  _scene_init, _grad_init = Scene.__init__, Grad.__init__

  def scene_init(self, *a, **k):
    _scene_init(self, *a, **k)
    for n in SCENE_METHODS:
        setattr(self, n, timed("scene." + n, getattr(self, n)))
    self.H.solve = timed("linear solve (H.solve)", self.H.solve)
    self.action = timed("scene.action", self.action)
    self.compute_reward = timed("scene.compute_reward", self.compute_reward)

  def grad_init(self, *a, **k):
    _grad_init(self, *a, **k)
    for n in GRAD_METHODS:
        setattr(self, n, timed("grad." + n, getattr(self, n)))
    _tg = self.transfer_grad

    def transfer_grad(step, *a2, **k2):
        r = _tg(step, *a2, **k2)
        if step == 1 and state["iter_done"] == 0:     # end of the first (compile) iteration
            state["iter_done"] = 1
            ti.sync(); reset()
        elif step == 1:
            state["iter_done"] += 1
        return r
    self.transfer_grad = transfer_grad

  Scene.__init__, Grad.__init__ = scene_init, grad_init


def report():
    if not stats:
        print("no stats collected (need ITERS >= 2)"); return
    n_it = max(state["iter_done"] - 1, 1)
    wall = time.time() - state["t0"]
    tot_fwd = stats.get("scene.time_step", [0, 0])[0]
    tot_bwd = stats.get("grad.transfer_grad", [0, 0])[0] + stats.get("grad.get_loss_fold", [0, 0])[0]
    out = {"arch": ARCH, "measured_iterations": n_it, "wall_s_per_iteration": wall / n_it,
           "forward_s_per_iteration": tot_fwd / n_it, "backward_s_per_iteration": tot_bwd / n_it, "stages": {}}
    print(f"\n=== profile ({ARCH}), {n_it} measured iterations; wall {wall / n_it:.2f} s/iteration "
          f"(forward {tot_fwd / n_it:.2f}, backward {tot_bwd / n_it:.2f}) ===")
    print(f"{'stage':36s} {'s/iter':>8s} {'calls/iter':>11s} {'ms/call':>9s} {'% of wall':>10s}")
    for name, (sec, calls) in sorted(stats.items(), key=lambda kv: -kv[1][0]):
        out["stages"][name] = {"s_per_iter": sec / n_it, "calls_per_iter": calls / n_it, "ms_per_call": 1000 * sec / max(calls, 1)}
        print(f"{name:36s} {sec / n_it:8.3f} {calls / n_it:11.1f} {1000 * sec / max(calls, 1):9.2f} {100 * sec / wall:9.1f}%")
    json.dump(out, open(os.path.join(HERE, f"profile_{ARCH}.json"), "w"), indent=1)


atexit.register(report)

# Run their script text in two parts (before / after its own imports) so the timers can be installed after ti.init, without editing it.
SCRIPT = "training/trajopt_folding.py"
MARK = "from thinshelllab.engine.analytic_grad_single import Grad\n"
head, tail = open(SCRIPT).read().split(MARK, 1)
ns = {"__name__": "__main__", "__file__": os.path.abspath(SCRIPT)}
exec(compile(head + MARK, SCRIPT, "exec"), ns)
install(ns["Scene"], ns["Grad"])
exec(compile(tail, SCRIPT, "exec"), ns)
