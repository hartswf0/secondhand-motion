"""Writes pose_agent_vN.json for the cloud: the f1 placement (chosen on the key sheets) carried by the
cloud's measured drift (top-edge profile matched frame to frame: about +0.97 px/frame right, -10 px up over
the shot), plus small extra lifts for the left lobe and the right end that the footage shows."""
import json, sys
base = {'left': [42.9, 171.7], 'right': [364.1, 143.6], 'lbase': [44.1, 153.8], 'mbase': [169.1, 115.5],
        'rbase': [251.9, 100.2], 'rlow': [323.4, 202.2]}
cust = json.loads(sys.argv[2])
extra = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
frames = [0, 1, 7, 13, 19, 25, 31, 37, 43, 49, 55, 61]
out = {}
for f in frames:
    t = (f - 1) / 60; dx = 0.97 * (f - 1); dy = -10 * t
    p = {}
    for k, v in list(base.items()) + list(cust.items()):
        e = extra.get(k, [0, 0])
        p[k] = [round(v[0] + dx + e[0] * max(t, 0), 1), round(v[1] + dy + e[1] * max(t, 0), 1)]
    out[str(f)] = p
json.dump(out, open(sys.argv[1], 'w'), indent=1)
