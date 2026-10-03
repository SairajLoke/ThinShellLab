"""Scripted crease test (no learning): press the U-shaped strip with a plate, lift the plate away, grab the free end of the top
layer with the fingertip, open the strip flat, release, and measure whether a crease stays.

Scene: code/task_scene/Scene_crease_test.py (the Folding scene plus a frozen 40 x 40 x 10 mm plate moved by script).
Phases (5 ms steps; speeds in mm per step):
  1 settle: the fingertip starts away from the paper, so the pre-curved strip opens to its rest shape (SETTLE steps)
  2 plate moves down (2 mm/step until 3 mm above the paper, then 0.5 mm/step) to PRESS_GAP above the bottom layer  (skipped with CT_PRESS=0: the control run)
  3 plate holds for HOLD steps
  4 plate lifts away (1 mm/step, then 3 mm/step)
  5 fingertip moves to the free end of the top layer; that row of 4 vertices is then attached to the fingertip
    (frozen and moved with it: an "attached grip", not friction)
  6 the attached row swings about the fold (pivot 1 mm above the bottom layer) to the far side until the strip is flat
    (<= 1 mm/step along the arc; the radius grows to the flap length so the paper is not pushed into the fold)
  7 release: the row is unfrozen, the fingertip moves up, then FINAL_SETTLE steps with velocity damping (CT_DAMP per step)
The far end of the bottom layer stays fixed (their set_frozen), so only one end of the strip is lifted.
Gravity stays off (as in Folding): Folding has no sheet-to-sheet contact, so a flap under gravity would fall through the bottom layer.

Measured at the end of each phase (metrics.json): per hinge row, the plastic rest angle (`ref_angle`, rad) and the current angle;
and the opening angle between the two halves (180 deg = flat). A crease that "stays" shows as rest angle left after the release,
and as an opening angle below 180 deg after settling.

Env: CT_NAME (output imgs/<CT_NAME>), CT_PRESS (1 press, 0 control), CT_RENDER (LuisaScript | none), CT_EVERY (render every Nth step,
default 4), CT_MU (sheet friction, default 0.5), CT_K (contact stiffness, Folding uses 1e4), CT_GAP (press gap in m, default 0.0014), CT_SLACK (slack of the opened strip, default 0.002), CT_DAMP (velocity factor per step in the final settle, default 0.97), TI_ARCH (cuda | cpu). Run from anywhere with PYTHONPATH containing data/AssetLoader:
    CT_NAME=crease_test_press TI_ARCH=cuda python tools/crease_test.py
    CT_NAME=crease_test_nopress CT_PRESS=0 TI_ARCH=cuda python tools/crease_test.py
Then: python tools/mix_to_multiply.py imgs/<name> && tools/render_scenes.sh imgs/<name> <name>
"""
import copy, json, math, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
NAME = os.environ.get("CT_NAME", "crease_test_press")
PRESS = os.environ.get("CT_PRESS", "1") == "1"
RENDER = os.environ.get("CT_RENDER", "LuisaScript")
EVERY = int(os.environ.get("CT_EVERY", "4"))
ARCH = os.environ.get("TI_ARCH", "cuda")
SLACK = float(os.environ.get("CT_SLACK", "0.002"))   # m of slack left in the opened strip
MAX_STEPS = int(os.environ.get("CT_MAX_STEPS", "0"))     # 0 = run everything
MU = float(os.environ.get("CT_MU", "0.5"))     # friction between the sheet and every body (table, fingertip, plate)

PRESS_GAP = float(os.environ.get("CT_GAP", "0.0014"))   # plate bottom height above the bottom layer's rest height
HOLD = 20
SETTLE = 40          # initial settling of the strip
FINAL_SETTLE = 150    # after the release, with velocity damping
DAMP = float(os.environ.get("CT_DAMP", "0.97"))   # per-step velocity factor during FINAL_SETTLE

os.chdir(os.path.join(REPO, "code"))
OUT = os.path.join("..", "imgs", NAME)
os.makedirs(OUT, exist_ok=True)

import taichi as ti
ti.init(ti.cuda if ARCH == "cuda" else ti.cpu, device_memory_fraction=0.5, default_fp=ti.f64, default_ip=ti.i32,
        fast_math=False, offline_cache=True)

from thinshelllab.task_scene.Scene_crease_test import Scene
from thinshelllab.engine.geometry import projection_query
import thinshelllab.engine.render_engine as RE

# ---------------------------------------------------------------- render settings: folding_2 look plus a style for the plate
settings = json.load(open("../data/scene_texture_options.json"))["folding_2"]
settings["elastics"] = settings["elastics"] + [{"type": "wood_1"}]
SETTINGS = os.path.join("..", "imgs", f"{NAME}_render_settings.json")
json.dump({"crease_test": settings}, open(SETTINGS, "w"), indent=1)

_pcm = RE.process_curve_mix
def _process_curve_mix(sys_, cloth_textures):   # same fix as tools/run_folding_luisa.py (convert_luisa.py:396 / :506)
    before = list(cloth_textures)
    _pcm(sys_, cloth_textures)
    for i, (old, new) in enumerate(zip(before, cloth_textures)):
        if new is not old and not hasattr(new, "both_sides"):
            wrapped = copy.copy(old); wrapped.texture = new; wrapped.curve = False
            cloth_textures[i] = wrapped
RE.process_curve_mix = _process_curve_mix

# ---------------------------------------------------------------- scene
sys_ = Scene(cloth_size=0.1)
sys_.cloths[0].Kb[None] = 400.0           # as in trajopt_folding.py
sys_.init_all()
sys_.mu_cloth_elastic[None] = MU           # trajopt_folding.py uses 5.0, which drags the paper along with the fingertip
cloth = sys_.cloths[0]
M1 = cloth.M + 1                           # vertices per grid row
plate = sys_.elastics[2]

renderer = RE.Renderer(sys_, "crease_test", option="LuisaScript", config_path=SETTINGS) if RENDER == "LuisaScript" else None
if renderer:
    renderer.set_save_dir(OUT)

dpos = ti.Vector.field(3, ti.f64, shape=1)
drot = ti.Vector.field(3, ti.f64, shape=1)

state = {"step": 0, "frame": 0, "attached": []}
log = {"name": NAME, "press": PRESS, "mu": MU, "k_contact": sys_.k_contact, "press_gap": PRESS_GAP, "dt": sys_.dt, "phases": []}


def positions():
    return sys_.pos.to_numpy()


def cloth_rows():
    p = positions()[: cloth.NV].reshape(cloth.N + 1, M1, 3)
    return p.mean(axis=1)                  # mean position of each grid row (row 0 = free end of the top layer)


def finger_bottom():
    p = positions()[sys_.elastics[1].offset: sys_.elastics[1].offset + sys_.elastics[1].n_verts]
    return p[:, 2].min()


def step(finger_d=(0, 0, 0), plate_d=(0, 0, 0), attached_d=None, damp=1.0):
    """One simulation step with scripted motions applied before it (as their scripts do for the gripper)."""
    if damp < 1.0:
        sys_.damp_sheet(damp)
    dpos[0] = ti.Vector(list(finger_d)); drot[0] = ti.Vector([0.0, 0.0, 0.0])
    sys_.action(state["step"], dpos, drot)
    if any(plate_d):
        sys_.move_plate(*plate_d)
    if attached_d is not None:
        for v, d in zip(state["attached"], attached_d):
            sys_.translate_vertices(v, 1, *d)
        sys_.push_down_pos()
    sys_.time_step(projection_query, state["step"])
    state["step"] += 1
    if state["step"] % 5 == 0 and not np.isfinite(sys_.pos.to_numpy()).all():
        print(f"NaN in positions at step {state['step']}: aborting", flush=True); sys.exit(2)
    if MAX_STEPS and state["step"] >= MAX_STEPS:        # smoke test: stop early but still export the scenes
        print(f"CT_MAX_STEPS reached at step {state['step']}", flush=True); raise StopIteration
    if renderer and state["step"] % EVERY == 0:
        renderer.render(str(state["frame"])); state["frame"] += 1


def move_finger(target, speed):
    p0 = sys_.gripper.pos.to_numpy()[0]
    d = np.asarray(target) - p0
    n = max(1, int(math.ceil(np.linalg.norm(d) / speed)))
    for _ in range(n):
        step(finger_d=d / n)


def hinge_summary():
    cloth.compute_normal_dir()
    out = np.zeros((cloth.NF * 3, 4))
    sys_.hinge_data(out)
    out = out[out[:, 3] > 0]
    rows = {}
    for r in sorted(set(out[:, 0])):
        sel = out[out[:, 0] == r]
        rows[f"{r:.1f}"] = {"rest_sum": float(sel[:, 1].sum()), "rest_maxabs": float(np.abs(sel[:, 1]).max()),
                            "angle_sum": float(sel[:, 2].sum()), "n_edges": int(len(sel))}
    return rows


def opening_angle():
    r = cloth_rows()
    tip = r[7:9].mean(axis=0)
    a, b = r[0] - tip, r[cloth.N] - tip
    return float(np.degrees(np.arccos(np.clip(a @ b / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))))


def checkpoint(name, t0):
    h = hinge_summary()
    crease = {k: v for k, v in h.items() if 6.0 <= float(k) <= 9.0}
    entry = {"phase": name, "end_step": state["step"], "seconds": round(time.time() - t0, 1),
             "opening_angle_deg": round(opening_angle(), 1),
             "rest_angle_sum_fold_rows_6_to_9": round(sum(v["rest_sum"] for v in crease.values()), 4),
             "rest_angle_sum_all": round(sum(v["rest_sum"] for v in h.values()), 4),
             "max_abs_rest_angle": round(max(v["rest_maxabs"] for v in h.values()), 4),
             "row_means_mm": np.round(cloth_rows() * 1000, 2).tolist(),
             "finger_mm": np.round(sys_.gripper.pos.to_numpy()[0] * 1000, 2).tolist(),
             "plate_bottom_mm": round(float(plate.F_x.to_numpy()[:, 2].min()) * 1000, 2),
             "hinge_rows": h}
    log["phases"].append(entry)
    print(f"[{name}] step {state['step']}  opening {entry['opening_angle_deg']} deg  rest-angle sum (rows 6-9) "
          f"{entry['rest_angle_sum_fold_rows_6_to_9']} rad  max |rest| {entry['max_abs_rest_angle']} rad  ({entry['seconds']} s)", flush=True)


try:
    T0 = time.time()
    if renderer:
        renderer.render(str(state["frame"])); state["frame"] += 1
    checkpoint("initial", T0)

    # 1: settle (the fingertip starts away from the paper, so the pre-curved strip opens to its rest shape)
    for _ in range(SETTLE):
        step()
    checkpoint("1_settled", T0)

    # 2-4: press, hold, lift
    if PRESS:
        bottom_layer_z = cloth_rows()[cloth.N][2]
        top_layer_z = positions()[: cloth.NV, 2].max()
        plate_bottom = plate.F_x.to_numpy()[:, 2].min()
        fast = plate_bottom - (top_layer_z + 0.003)          # approach at 2 mm/step until 3 mm above the paper
        n = int(math.ceil(fast / 0.002))
        for _ in range(n):
            step(plate_d=(0, 0, -fast / n))
        slow = (top_layer_z + 0.003) - (bottom_layer_z + PRESS_GAP)
        n = int(math.ceil(slow / 0.0005))
        for _ in range(n):
            step(plate_d=(0, 0, -slow / n))
        checkpoint("2_pressed", T0)
        for _ in range(HOLD):
            step()
        checkpoint("3_held", T0)
        for _ in range(10):
            step(plate_d=(0, 0, 0.001))
        while plate.F_x.to_numpy()[:, 2].min() < 0.09:
            step(plate_d=(0, 0, 0.003))
        checkpoint("4_plate_lifted", T0)
    else:
        for _ in range(HOLD):
            step()
        checkpoint("2-4_no_press_wait", T0)

    # 5: fingertip onto the free end (row 0 of the top layer), then attach that row
    end = cloth_rows()[0]
    f = sys_.gripper.pos.to_numpy()[0]
    lift = f[2] - finger_bottom()                       # fingertip centre height above its lowest point
    target = np.array([end[0] - 0.002, f[1], end[2] + lift + sys_.eps_contact])
    move_finger(np.array([target[0], f[1], max(f[2], target[2] + 0.01)]), 0.002)
    move_finger(target, 0.001)
    state["attached"] = list(range(0, M1))              # vertex indices of row 0
    for v in state["attached"]:
        sys_.freeze_body(v, 1, 1)
    checkpoint("5_grabbed", T0)

    # 6: swing row 0 about the fold tip (axis along y) to the far side, flat
    pos = positions()
    rows = cloth_rows()
    axis_x, axis_z = rows[:, 0].min(), rows[cloth.N][2] + 0.001   # pivot: the leftmost row (the fold), 1 mm above the bottom layer
    rel = np.array([[pos[v][0] - axis_x, pos[v][2] - axis_z] for v in state["attached"]])
    radius = float(np.linalg.norm(rel.mean(axis=0)))
    phi0 = float(math.atan2(rel.mean(axis=0)[1], rel.mean(axis=0)[0]))
    row15_x = rows[cloth.N][0]
    r_end = max(radius, axis_x - (row15_x - cloth.N * cloth.dx + SLACK))   # row 0 ends SLACK short of the full strip length from the fixed end
    n = int(math.ceil(max(radius, r_end) * (math.pi - phi0) / 0.001))
    print(f"  arc: axis x {axis_x * 1000:.1f} z {axis_z * 1000:.1f} mm, radius {radius * 1000:.1f} -> {r_end * 1000:.1f} mm, phi0 {math.degrees(phi0):.0f} deg, {n} steps", flush=True)
    finger_rel = sys_.gripper.pos.to_numpy()[0] - pos[state["attached"]].mean(axis=0)
    for k in range(1, n + 1):
        phi = phi0 + (math.pi - phi0) * k / n
        cur = positions()
        new = []
        for v, (rx, rz) in zip(state["attached"], rel):
            r = math.hypot(rx, rz) + (r_end - radius) * k / n     # grow to the flap length so the swing never pushes paper into the fold
            new.append(np.array([axis_x + r * math.cos(phi), cur[v][1], axis_z + r * math.sin(phi)]) - cur[v])
        mean_new = np.mean([cur[v] + d for v, d in zip(state["attached"], new)], axis=0)
        finger_d = (mean_new + finger_rel) - sys_.gripper.pos.to_numpy()[0]
        step(finger_d=finger_d, attached_d=new)
        if k % 20 == 0 or k == n:
            print(f"  arc {k}/{n}: phi {math.degrees(phi):.0f} deg, row0 now {np.round(positions()[state['attached']].mean(axis=0) * 1000, 1)} mm, "
                  f"target {np.round(mean_new * 1000, 1)} mm", flush=True)
    checkpoint("6_opened", T0)

    # 7: release, fingertip up, settle
    for v in state["attached"]:
        sys_.freeze_body(v, 1, 0)
    state["attached"] = []
    move_finger(sys_.gripper.pos.to_numpy()[0] + np.array([0, 0, 0.015]), 0.0005)
    openings = []
    for k in range(FINAL_SETTLE):
        step(damp=DAMP)
        if k >= FINAL_SETTLE - 20:
            openings.append(opening_angle())
    checkpoint("7_released_settled", T0)
    log["final_opening_mean_last20_deg"] = round(float(np.mean(openings)), 1)
    log["final_opening_range_last20_deg"] = [round(float(min(openings)), 1), round(float(max(openings)), 1)]
    print(f"final opening, last 20 steps: mean {log['final_opening_mean_last20_deg']} deg, "
          f"range {log['final_opening_range_last20_deg']}", flush=True)


except StopIteration:
    pass
log["steps"] = state["step"]; log["rendered_frames"] = state["frame"]; log["render_every"] = EVERY
if renderer:
    renderer.end_rendering(0)                   # export (this wipes OUT first, so metrics are written after it)
json.dump(log, open(os.path.join(OUT, "metrics.json"), "w"), indent=1)
np.save(os.path.join(OUT, "final_positions.npy"), positions())
print(f"done: {state['step']} steps, {state['frame']} frames, {time.time() - T0:.0f} s -> {OUT}", flush=True)
