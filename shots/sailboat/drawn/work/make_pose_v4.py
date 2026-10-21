"""Pose keys v4 for the sailboat: v3 un-mirrored. The doodle keeps its own facing (sail on the left of the mast,
raised end stroke of the hull on the right, as in c.png and in the film); each key is placed so the drawing's
bounding box sits where v3's did, so the path and timing are unchanged."""
import json, numpy as np, importlib.util
from pathlib import Path
R = Path('/home/claude/cartoon-archive')
spec = importlib.util.spec_from_file_location('sb', R / 'rigs/sailboat.py'); sb = importlib.util.module_from_spec(spec); spec.loader.exec_module(sb)
v3 = json.load(open(R / 'shots/sailboat-sam/pose_agent_v3.json'))
def box(p):
    a = np.concatenate([np.array(q, float) for q in sb.draw(p)]); return a.min(0), a.max(0)
out = {}
for f, p in v3.items():
    lo, hi = box(p)
    q = dict(p, _face=1.0)
    lo2, hi2 = box(q)
    d = (lo + hi) / 2 - (lo2 + hi2) / 2; d[1] = hi[1] - hi2[1]
    q['hull'] = [round(p['hull'][0] + d[0], 1), round(p['hull'][1] + d[1], 1)]
    q['top'] = [round(p['top'][0] + d[0], 1), round(p['top'][1] + d[1], 1)]
    out[f] = q; print(f, q)
json.dump(out, open(R / 'shots/sailboat-sam/pose_agent_v4.json', 'w'), indent=1)
