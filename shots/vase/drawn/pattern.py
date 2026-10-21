"""Writes shots/vase/drawn/k000..k037.json: the rig's own drawing at every frame (unchanged) plus the pot's
painted pattern as extra marks, and writes the hand's per-frame copies into rigs/vase_scene.json.

Marks: each mark is one real Quick, Draw! leaf doodle placed on the vase body as on a cylinder:
x = centre(y) + halfwidth(y) * sin(angle + turn). All six marks are on every frame with the same points, so no
mark appears or vanishes between two frames. A part of a mark that has turned past the right edge is pressed onto
the body outline and drawn in toward the mark's middle height; a part still behind the hand's fingertips on the
left is pressed onto the hand's own outline at that height, so it lies under the finger lines. So a mark thins in from the fingertips
over several frames and thins out into the right outline over several frames, continuously, down to zero width.

turn(f) = the film's measured pattern slide (phase correlation of the painted band, rows 140-235, cols 110-270,
frame to frame) / the film's body half-width (135 px). In frames 0-7 the film's slide measures 0 to 2.5 px a
frame (the pot is already being eased round); each of those steps is kept to at least 1.2 px so the marks step
right from the second frame on.

Hand: the hand doodle (quickdraw:6146752153387008, fitted once and kept in hand_base.json) is copied once per
frame; its fingers slide a little right and the lower fingers a little down as the bowl turns, in proportion to
the turn, as the film's fingers creep along the rim. usage: python3 shots/vase/drawn/pattern.py"""
import json, math
from pathlib import Path
import numpy as np, cv2
ROOT = Path(__file__).resolve().parents[3]; D = ROOT / 'shots/vase/drawn'; S = ROOT / 'shots/vase-sam'
n = json.load(open(S / 'clip.json'))['n']
G = [cv2.imread(str(S / 'frames' / f'f{f:03d}.jpg'), 0).astype(np.float32)[140:235, 110:270] for f in range(n)]
win = cv2.createHanningWindow(G[0].shape[::-1], cv2.CV_32F); step = [0.0]
for f in range(n - 1):
    (dx, dy), r = cv2.phaseCorrelate(G[f], G[f + 1], win); step.append(max(dx, 1.2 if f < 7 else 0.0))
c = np.cumsum(step); sig = 1.0; rad = 3; w = np.exp(-0.5 * (np.arange(-rad, rad + 1) / sig) ** 2); w /= w.sum()
pad = np.r_[c[0] - (c[rad:0:-1] - c[0]), c, c[-1] + (c[-1] - c[-2:-rad - 2:-1])]   # odd extension keeps the ends moving
c = np.array([pad[i:i + 2 * rad + 1] @ w for i in range(n)]); c -= c[0]
turn = c / 135.0; s_turn = turn / turn[-1]
rig = json.load(open(ROOT / 'shots/vase-gwp/rig_frames.json'))

# hand, one copy per frame
H0 = [np.array(s, float) for s in json.load(open(D / 'hand_base.json'))['strokes']]
def hand(f):
    out = []
    for s in H0:
        x, y = s[:, 0], s[:, 1]; wx = np.clip((x - 62) / 50, 0, 1); ly = np.clip((y - 195) / 45, 0, 1)
        q = s.copy(); q[:, 0] += wx * (2.5 + 4.5 * ly) * s_turn[f]; q[:, 1] += wx * (-1.0 + 3.0 * ly) * s_turn[f]
        out.append(q)
    return out
HANDS = [hand(f) for f in range(n)]
def hand_right(f, y):   # the right-most crossing of the hand's own outline at height y (None above or below the hand)
    xs = []
    for q in HANDS[f]:
        for (x0, y0), (x1, y1) in zip(q[:-1], q[1:]):
            if (y0 - y) * (y1 - y) <= 0 and y0 != y1: xs.append(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
    return max(xs) if xs else None
sc = json.load(open(ROOT / 'rigs/vase_scene.json'))
sc['objects'] = [o for o in sc['objects'] if not o['id'].startswith('hand')]
for f in range(n):
    sc['objects'].append({'id': f'hand{f:02d}', 'plane': 'char', 'class': 'hand', 'visible': [f, f],
                          'why': f'the hand reaching in from the left that holds and turns the pot: the Quick, Draw! hand doodle 6146752153387008, frame {f}, fingers slid {100 * s_turn[f]:.0f}% of the way along the rim',
                          'strokes': np.round(HANDS[f][0:], 1).tolist()})
json.dump(sc, open(ROOT / 'rigs/vase_scene.json', 'w'), indent=1)

# marks
rows = [json.loads(l) for l in open(ROOT / 'data/quickdraw/leaf.part').read().splitlines()[:-1]]
def unit(kid):
    r = next(r for r in rows if str(r['key_id']) == kid)
    L = [np.array(list(zip(*s)), float) for s in r['drawing']]; A = np.concatenate(L); mn, mx = A.min(0), A.max(0)
    L = [(s - (mn + mx) / 2) / (mx - mn) for s in L]
    # each segment split into even sub-steps (the doodle's own vertices kept), so a part pressed onto the hand's
    # outline follows that outline closely instead of cutting across the fingers in long chords
    return [np.vstack([a + (b - a) * t for a, b in zip(q[:-1], q[1:]) for t in np.arange(8) / 8] + [q[-1:]]) for q in L]
MARKS = [(unit('4928285815341056'), 0.40, 58.0, 212.0), (unit('6535184159604736'), 0.62, 60.0, 210.0)]
def side_x(stroke, y):
    s = np.array(stroke); i = np.argsort(s[:, 1]); return float(np.interp(y, s[i, 1], s[i, 0]))
N = 6; FADE = 0.15   # radians behind an edge over which a hidden part is drawn in to one point
for f in range(n):
    fr = rig[f]; extra = {}; P = np.concatenate(HANDS[f]); ty = float(P[np.argmax(P[:, 0]), 1])   # the lowest, longest fingertip
    def body(y):
        xl, xr = side_x(fr[3], y), side_x(fr[1], y); xl, xr = min(xl, xr), max(xl, xr); return (xl + xr) / 2, (xr - xl) / 2
    def a_left(y):   # angle of the left horizon at height y: the hand's outline where the hand covers the body, else the body outline
        cx, hw = body(y); tx = hand_right(f, y); tx = cx - hw if tx is None else max(tx, cx - hw)
        return math.asin(max(-1.0, min(1.0, (tx - cx) / hw)))
    for k in range(N):
        a0 = -math.pi + (k + 0.5) * 2 * math.pi / N + turn[f]
        L, LW, LH, Y0 = MARKS[k % 2]
        for j, s in enumerate(L):
            pts = []
            for u, v in s:
                y = Y0 + v * LH; a = a0 + u * LW; aL = a_left(y)
                if a > math.pi / 2:      # round the right edge: onto the outline, drawn in toward the mark's middle
                    t = min(1.0, (a - math.pi / 2) / FADE); y = y + (Y0 - y) * t; a = math.pi / 2
                elif a < aL:             # behind the fingers: onto the hand's own outline at that height
                    a = aL
                cx, hw = body(y); pts.append([round(cx + hw * math.sin(a), 1), round(y, 1)])
            extra[f'leaf{k}{"abcdef"[j]}'] = pts
    json.dump({'why': ('the pot turned by %.2f rad from the first frame (measured pattern slide %.0f px); the leaves of the painted band are where that turn puts them' % (turn[f], c[f])),
               'strokes': fr, 'extra': extra}, open(D / f'k{f:03d}.json', 'w'))
print('turn', np.round(turn, 3).tolist())
