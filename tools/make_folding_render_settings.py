"""Creates tools/folding_render_settings.json: a copy of data/scene_texture_options.json plus one extra entry, "folding".

Why: with --render_option LuisaScript, training/trajopt_folding.py looks up the scene name "folding", which the repo's
settings file does not contain. Its closest entries fail in this repo version:
  "folding_2"    -> AttributeError: 'TextureOptions' object has no attribute 'both_sides' (engine/convert_luisa.py:506)
  "folding_real" -> KeyError: 'pure_1_solid' (engine/render_engine.py:121; no such fingertip preset is defined)
The new entry is "folding_real" with the existing "pure_1" fingertip preset. The repo's own file is left unchanged.

    python tools/make_folding_render_settings.py            # writes tools/folding_render_settings.json
    OUT=/tmp/x.json python tools/make_folding_render_settings.py
"""
import copy, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(REPO, "data", "scene_texture_options.json")
DST = os.environ.get("OUT", os.path.join(HERE, "folding_render_settings.json"))

d = json.load(open(SRC))
entry = copy.deepcopy(d["folding_real"])
entry["elastics"] = [{"type": "pure_1"}]
d["folding"] = entry
json.dump(d, open(DST, "w"), indent=1)
print("wrote", DST)
