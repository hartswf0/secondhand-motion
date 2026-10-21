"""Draws the cat's keys from its own doodle (rigs/cat_spec.json): D0 is the doodle as drawn (front),
D60 is the same strokes redrawn for a three-quarter view facing screen right. Each key blends D0->D60 by
`turn`, then places it on the film's eye line (scale, roll, eye midpoint). Run: python3 shots/cat/drawn/make_keys.py"""
import json, math
from pathlib import Path
import numpy as np
HERE = Path(__file__).parent; ROOT = HERE.parent.parent.parent
D0 = [np.array(s, float) for s in json.load(open(ROOT / 'rigs' / 'cat_spec.json'))['strokes']]

def feat(s, c, sx, dx=0, dy=0):   # squeeze a stroke about its centre c, then move it
    s = s.copy(); s[:, 0] = c[0] + (s[:, 0] - c[0]) * sx + dx; s[:, 1] += dy; return s

D60 = [None] * 11
# outline: back of head grows to the left, the right side becomes the brow, nose bump and muzzle
D60[0] = np.array([[150, 37], [149, 33], [104, 31], [68, 46], [56, 80], [60, 120], [92, 145], [134, 149],
                   [168, 141], [188, 128], [198, 114], [193, 98], [196, 66], [193, 46], [185, 35], [147, 32]], float)
# eyes: the near (left) eye moves toward the middle, the far (right) eye narrows at the brow edge
D60[9] = feat(D0[9], (96, 87), 0.8, 148 - 96, 2)
D60[10] = feat(D0[10], (160, 91), 0.35, 184 - 160, 0)
# ears: the near ear slides back over the crown, the far ear sits at the front and leans forward
D60[5] = D0[5] + [-34, 6]
e = feat(D0[4].copy(), (188, 30), 0.8, -4, 6); b = (e[0] + e[-1]) / 2; q = math.radians(38)
D60[4] = (e - b) @ np.array([[math.cos(q), -math.sin(q)], [math.sin(q), math.cos(q)]]).T + b   # laid back toward screen right, as the film's far ear
# far-side whiskers come off the muzzle, same angles
for i, (x, y) in zip((1, 2, 3), ((197, 108), (195, 118), (188, 127))):
    s = D0[i]; D60[i] = (s - s[0]) * 0.6 + [x, y]
# near-side whiskers still start at the near eye, as the doodler drew them, shorter (they point back)
for i in (6, 7, 8):
    s = D0[i]; o = s[0] + [148 - 96, 2]; D60[i] = (s - s[0]) * [0.6, 0.8] + o + [6, 4]

def eyes(D):
    return D[9].mean(0), D[10].mean(0)

def blend(a, b, t):
    n = max(len(a), len(b)); return resample(a, n) * (1 - t) + resample(b, n) * t

def resample(s, n):
    if len(s) == n: return s
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(s, axis=0).T))]; t = np.linspace(0, d[-1], n)
    return np.c_[np.interp(t, d, s[:, 0]), np.interp(t, d, s[:, 1])]

def place(turn, up, E, ang, s):
    D = [blend(a, b, turn) for a, b in zip(D0, D60)]
    # chin up: eyes and whiskers ride higher on the face, the lower outline foreshortens toward the eyes
    for i in (1, 2, 3, 6, 7, 8, 9, 10): D[i] = D[i] - [0, 13 * up]
    o = D[0].copy(); lo = o[:, 1] > 80; o[lo, 1] -= up * 0.22 * (o[lo, 1] - 80); D[0] = o
    l, r = eyes(D); m = (l + r) / 2; a0 = math.atan2(r[1] - l[1], r[0] - l[0])
    th = math.radians(ang) - a0; R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    return [((d - m) @ R.T * s + E).round(1).tolist() for d in D]

# frame: (turn, film eye midpoint, film eye-line angle in degrees, scale, why)
KEYS = {
 0:  (0.0, 1.0, (162, 104), -11.5, 1.08, 'Start: chin raised, head tilted up and a little to screen left, eyes half shut; the held pose of the first four seconds.'),
 16: (0.0, 1.0, (162, 104), -11.5, 1.08, 'Still holding the raised head: the film barely moves here, so the drawing is pinned.'),
 30: (0.0, 1.0, (162, 104), -11.5, 1.08, 'Still holding the raised head.'),
 43: (0.0, 1.0, (162, 105), -11.5, 1.08, 'End of the hold: the last frame of the raised head before it drops.'),
 45: (0.06, 0.85, (165, 107), -11.0, 1.08, 'Anticipation: the chin just starts to drop.'),
 47: (0.22, 0.6, (175, 113), -10.5, 1.10, 'Drop and turn begin: eyes and whisker roots start sliding to the right inside the outline.'),
 49: (0.42, 0.35, (192, 121), -10.0, 1.13, 'Turning: features a third of the way across the face, right side of the outline flattening, head lowering.'),
 51: (0.62, 0.15, (210, 130), -9.0, 1.17, 'The line: the cat swings to face screen right, eyes now clearly right of centre.'),
 53: (0.80, 0.0, (226, 138), -9.0, 1.21, 'Turn finishing: three-quarter view facing right, far eye pressed against the flat right side, far ear laid back.'),
 56: (1.0, 0.0, (244, 145), -9.0, 1.24, 'Settle: full three-quarter view facing right, the head arrives low and right and stops.'),
 61: (1.0, 0.0, (246, 145), -9.0, 1.24, 'Holds to the end looking right.'),
}

if __name__ == '__main__':
    for f, (t, u, E, a, s, why) in KEYS.items():
        p = HERE / f'k{f:03d}.json'
        old = json.load(open(p)) if p.exists() else {}
        json.dump({'why': why, 'strokes': place(t, u, np.array(E, float), a, s), 'extra': old.get('extra', {})}, open(p, 'w'))
    print('wrote', sorted(KEYS))
