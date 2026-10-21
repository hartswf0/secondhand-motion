"""Pose keys v3 for the sailboat: the doodle mirrored (sail aft of the mast, to the right, as the barge's is),
narrowed in x early (seen bow-quarter) and widening late, scaled by how far the hull sits below the horizon."""
import json, sys, numpy as np
from pathlib import Path
R = Path('/home/claude/cartoon-archive'); sys.path.insert(0, str(R / 'rigs'))
import importlib.util
spec = importlib.util.spec_from_file_location('sb', R / 'rigs/sailboat.py'); sb = importlib.util.module_from_spec(spec); spec.loader.exec_module(sb)
from PIL import Image, ImageDraw
M = json.load(open(R / 'shots/sailboat-sam/masks.json'))
def meas(f):
    im = Image.new('L', (384, 288), 0); d = ImageDraw.Draw(im)
    for p in M[str(f)]:
        if len(p) > 2: d.polygon([tuple(q) for q in p], fill=255)
    a = np.array(im) > 0; ys, xs = np.nonzero(a); bot = ys.max(); band = a[bot - 30:bot - 5]; bx = np.nonzero(band.any(0))[0]
    return bot, bx.min(), bx.max()
keys = [0, 16, 32, 42, 48, 54, 60, 66, 73]
raw = {f: meas(f) for f in keys}
raw[73] = (247, 148, 383)
fs = np.array(keys); B = np.array([raw[f][0] for f in keys], float); L = np.array([raw[f][1] for f in keys], float)
# smooth bottom so size grows steadily
Bs = np.maximum.accumulate(np.array([np.mean(B[max(0, i - 1):i + 2]) for i in range(len(B))])); Bs[0] = B[0]
Ls = np.array([np.mean(L[max(0, i - 1):i + 2]) for i in range(len(L))]); Ls[0] = L[0]; Ls[-1] = L[-1]
H0 = 167.6
def S(f, b): return float(np.interp(f, [0, 28, 48, 60, 73], [0.87, 1.05, 1.27, 1.5, 1.92]))
def XS(f): return float(np.interp(f, [0, 36, 56, 73], [0.55, 0.57, 0.62, 0.66]))
out = {}
for i, f in enumerate(keys):
    s = S(f, Bs[i]); xs = XS(f)
    pose = {'hull': [0.0, 0.0], 'top': [5 * s, -180 * s], '_face': -1.0, '_xscale': xs}
    st = sb.draw(pose); a = np.concatenate([np.array(q) for q in st])
    hull = np.array(st[1]); dx = (Ls[i] - 6) - hull[:, 0].min(); dy = Bs[i] - a[:, 1].max()
    pose['hull'] = [round(dx, 1), round(dy, 1)]; pose['top'] = [round(5 * s + dx, 1), round(-180 * s + dy, 1)]
    pose['_xscale'] = round(xs, 3)
    out[str(f)] = pose
    print(f, round(s, 2), xs, pose['hull'], pose['top'])
json.dump(out, open(R / 'shots/sailboat-sam/pose_agent_v3.json', 'w'), indent=1)
