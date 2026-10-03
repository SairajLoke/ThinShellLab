"""Rewrites 'mix { top: T bottom: B factor {..} method {"multiply"} }' (not available in the LuisaRender build) into
'multiply { a: T b: B }' (available) in generated scene_*.luisa files. Originals are kept in <dir>/scenes_orig/."""
import re, shutil, sys, os, glob
d = sys.argv[1]
os.makedirs(f"{d}/scenes_orig", exist_ok=True)
def convert(text):
    out, i, n = [], 0, 0
    while True:
        m = re.search(r"(\w+): mix \{", text[i:])
        if not m: out.append(text[i:]); break
        s = i + m.start(); b = i + m.end()          # position after the opening brace
        depth, j = 1, b
        while depth:
            depth += {"{": 1, "}": -1}.get(text[j], 0); j += 1
        block = text[b:j-1]
        top = re.search(r"top: (.*?)\n\t\tbottom:", block, re.S).group(1)
        bottom = re.search(r"bottom: (.*?)\n\t\tfactor", block, re.S).group(1)
        assert 'method { "multiply" }' in block
        out.append(text[i:s] + f"{m.group(1)}: multiply {{\n\t\ta: {top}\n\t\tb: {bottom}\n\t}}")
        i, n = j, n + 1
    return "".join(out), n
tot = 0
for f in sorted(glob.glob(f"{d}/scene_*.luisa")):
    shutil.copy(f, f"{d}/scenes_orig/{os.path.basename(f)}")
    new, n = convert(open(f).read()); tot += n
    open(f, "w").write(new)
print("converted", tot, "mix blocks in", len(glob.glob(f"{d}/scene_*.luisa")), "files")
