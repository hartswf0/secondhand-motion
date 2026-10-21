"""Writes shots/vase/drawn/k000..k037.json: the rig's own drawing at every frame (unchanged) plus the pot's
painted pattern as extra marks. Each mark is one real Quick, Draw! leaf doodle, placed on the vase body as on a
cylinder: x = centre(y) + halfwidth(y) * sin(angle + turn), so marks slide right, narrow toward the edge and leave
it, as the film's pattern does while the hand turns the pot. turn(f) = the film's measured pattern slide (phase
correlation of the painted band, rows 140-235, cols 110-270, frame to frame, summed, smoothed) / the film's body
half-width (135 px). usage: python3 shots/vase/drawn/pattern.py"""
import json, math
from pathlib import Path
import numpy as np, cv2
ROOT = Path(__file__).resolve().parents[3]; D = ROOT / 'shots/vase/drawn'; S = ROOT / 'shots/vase-sam'
n = json.load(open(S / 'clip.json'))['n']
G = [cv2.imread(str(S / 'frames' / f'f{f:03d}.jpg'), 0).astype(np.float32)[140:235, 110:270] for f in range(n)]
win = cv2.createHanningWindow(G[0].shape[::-1], cv2.CV_32F); c = [0.0]
for f in range(n - 1):
    (dx, dy), r = cv2.phaseCorrelate(G[f], G[f + 1], win); c.append(c[-1] + max(dx, 0.0))
c = np.array(c); sig = 1.5; rad = 5; w = np.exp(-0.5 * (np.arange(-rad, rad + 1) / sig) ** 2); w /= w.sum()
pad = np.r_[np.repeat(c[:1], rad), c, np.repeat(c[-1:], rad)]; c = np.array([pad[i:i + 2 * rad + 1] @ w for i in range(n)])
turn = c / 135.0
rig = json.load(open(ROOT / 'shots/vase-gwp/rig_frames.json'))
LEAF_ID = '4928285815341056'
rows = [json.loads(l) for l in open(ROOT / 'data/quickdraw/leaf.part').read().splitlines()[:-1]]
leaf = next(r for r in rows if str(r['key_id']) == LEAF_ID)
L = [np.array(list(zip(*s)), float) for s in leaf['drawing']]; A = np.concatenate(L); mn, mx = A.min(0), A.max(0)
L = [(s - (mn + mx) / 2) / (mx - mn) for s in L]          # leaf in a unit box centred on 0
def side_x(stroke, y):
    s = np.array(stroke); i = np.argsort(s[:, 1]); return float(np.interp(y, s[i, 1], s[i, 0]))
N = 7; LW, LH = 0.42, 58.0; Y0 = 212.0                       # 7 leaves round the pot; width in radians, height px
for f in range(n):
    fr = rig[f]; extra = {}
    for k in range(N):
        a0 = -math.pi + (k + 0.5) * 2 * math.pi / N + turn[f]
        if math.cos(a0) < 0.12: continue
        for j, s in enumerate(L):
            pts = []
            for u, v in s:
                y = Y0 + v * LH; xl, xr = side_x(fr[3], y), side_x(fr[1], y)
                xl, xr = min(xl, xr), max(xl, xr); cx, hw = (xl + xr) / 2, (xr - xl) / 2 * 0.9
                a = a0 + u * LW; pts.append([round(cx + hw * math.sin(max(-1.45, min(1.45, a))), 1), round(y, 1)])
            extra[f'leaf{k}{"abcdef"[j]}'] = pts
    json.dump({'why': ('the pot turned by %.2f rad from the first frame (measured pattern slide %.0f px); the leaves of the painted band are where that turn puts them' % (turn[f], c[f])),
               'strokes': fr, 'extra': extra}, open(D / f'k{f:03d}.json', 'w'))
print('turn', np.round(turn, 2).tolist())
