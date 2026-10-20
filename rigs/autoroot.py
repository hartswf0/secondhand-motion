"""First-pass keys for any doodle rig, from the SAM silhouettes alone (the giraffe's autopose, generalised).

At each key frame the doodle's anchor points are placed by one transform that maps the doodle's bounding box
onto the silhouette's (uniform scale from the silhouette's area, so the doodle keeps its proportions), facing
the way the silhouette's centre moves (or a fixed facing). Every anchor the spec names gets a point, so the
in-betweener has a full pose. This is a starting point for correction by eye on tools/key_grid.py, never a
finished key.

usage: python3 rigs/autoroot.py <slug> <every-n-frames> [left|right|motion]  -> shots/<slug>-sam/pose_auto.json
"""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from sam_keys import raster


def run(slug, every, facing='motion'):
    d = ROOT / 'shots' / f'{slug}-sam'; clip = json.load(open(d / 'clip.json')); n, W, H = clip['n'], clip['W'], clip['H']
    sp = json.load(open(ROOT / 'rigs' / f"{slug.replace('-', '_')}_spec.json")); M = json.load(open(d / 'masks.json'))
    pts = np.concatenate([np.array(s, float) for s in sp['strokes']]); lo, hi = pts.min(0), pts.max(0); dsz = hi - lo
    A = {k: np.array(v, float) for k, v in sp['anchors'].items()}
    cs = []
    for f in range(n):
        m = raster(M[str(f)], W, H); ys, xs = np.nonzero(m)
        cs.append((np.array([xs.min(), ys.min()]), np.array([xs.max(), ys.max()]), np.array([xs.mean(), ys.mean()])) if len(xs) else None)
    frames = sorted(set(list(range(0, n, every)) + [n - 1] + clip.get('keys', [])))
    out = {}
    for f in frames:
        if cs[f] is None: continue
        b0, b1, c = cs[f]
        if facing == 'motion':
            g = [cs[j][2] for j in range(max(0, f - 3), min(n, f + 4)) if cs[j] is not None]
            dx = g[-1][0] - g[0][0]; face = 1 if dx >= 0 else -1
        else: face = 1 if facing == 'right' else -1
        flip = face != sp.get('facing', 1)
        s = min((b1 - b0)[0] / max(dsz[0], 1), (b1 - b0)[1] / max(dsz[1], 1))
        mid = (b0 + b1) / 2; dmid = (lo + hi) / 2
        def place(p):
            q = p.copy()
            if flip: q[0] = lo[0] + hi[0] - q[0]
            return [round(float(mid[0] + (q[0] - dmid[0]) * s), 1), round(float(mid[1] + (q[1] - dmid[1]) * s), 1)]
        out[str(f)] = {k: place(v) for k, v in A.items()}
    json.dump(out, open(d / 'pose_auto.json', 'w'), indent=0)
    print(slug, len(out), 'auto keys')


if __name__ == '__main__':
    run(sys.argv[1], int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else 'motion')
