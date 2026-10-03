# results/crease_test: scripted press / pick / open runs (branch `crease-test`)

Metrics and logs only (videos and scenes are in the Hugging Face dataset `drakedrake/ppr-sim`, `tsl/crease_test/`). Script: `tools/crease_test.py`, scene: `code/task_scene/Scene_crease_test.py`. Overview and caveats: `../../progress-till-now.md`.

| run | what | notes |
|---|---|---|
| `crease_smoke` | first complete run, default config (sheet friction 0.5, `k_contact` 1e4, press gap 1.4 mm), no rendering | metrics per phase: opening angle, per-row plastic rest angles |
| `crease_test_press` | the same config with LuisaRender export (v1 video) | the video shows a flung-up flap after release (compressed strip, no damping) |
| `crease_k1e6` | contact stiffness 1e6 | paper pushed 4 mm below the table during the press |
| `crease_k1e5`, `crease_mu0.1`, `crease_mu0.1_gap3` | contact stiffness 1e5; sheet friction 0.1; friction 0.1 with 3 mm press gap | all went NaN in the press phase (log only) |
| `crease_v2_press`, `crease_v2_nopress` | version 2 (2 mm slack at the end of the swing, sheet velocity damping x0.97 per step for 150 steps after release), press run and control without press | complete; final opening 155.1 (press) vs 145.4 degrees (control); no table penetration; gravity off, so the released strip does not lie flat (see `progress-till-now.md`) |

`metrics.json` per run: `phases[]` with `opening_angle_deg`, `row_means_mm` (mean position of each grid row), `hinge_rows` (per hinge row: sum of plastic rest angles in radians, number of edges) and the sum of rest angles over rows 6-9. Per-edge degrees = `rest_sum / n_edges * 57.3`.
