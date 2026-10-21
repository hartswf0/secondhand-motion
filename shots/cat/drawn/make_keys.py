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
D60[0] = np.array([[150, 37], [149, 33], [100, 31], [58, 46], [40, 80], [44, 120], [82, 146], [128, 150],
                   [165, 143], [184, 131], [200, 116], [186, 97], [190, 66], [188, 45], [180, 34], [147, 32]], float)
# eyes: the near (left) eye moves toward the middle, the far (right) eye narrows at the brow edge
D60[9] = feat(D0[9], (96, 87), 0.85, 128 - 96, 2)
D60[10] = feat(D0[10], (160, 91), 0.4, 171 - 160, 0)
# ears: the near ear slides back over the crown, the far ear sits at the front and leans forward
D60[5] = D0[5] + [-40, 6]
e = D0[4].copy(); D60[4] = feat(e, (188, 30), 0.8, -2, 4); D60[4][1:3, 0] += 8
# far-side whiskers come off the muzzle, same angles
for i, (x, y) in zip((1, 2, 3), ((195, 111), (192, 121), (183, 131))):
    s = D0[i]; D60[i] = (s - s[0]) * 0.85 + [x, y]
# near-side whiskers still start at the near eye, as the doodler drew them, shorter (they point back)
for i in (6, 7, 8):
    s = D0[i]; o = s[0] + [128 - 96, 2]; D60[i] = (s - s[0]) * [0.6, 0.8] + o + [6, 4]

def eyes(D):
    return D[9].mean(0), D[10].mean(0)

def blend(a, b, t):
    n = max(len(a), len(b)); return resample(a, n) * (1 - t) + resample(b, n) * t

def resample(s, n):
    if len(s) == n: return s
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(s, axis=0).T))]; t = np.linspace(0, d[-1], n)
    return np.c_[np.interp(t, d, s[:, 0]), np.interp(t, d, s[:, 1])]

def place(turn, E, ang, s, ex=None):
    D = [blend(a, b, turn) for a, b in zip(D0, D60)]
    l, r = eyes(D); m = (l + r) / 2; a0 = math.atan2(r[1] - l[1], r[0] - l[0])
    th = math.radians(ang) - a0; R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    return [((d - m) @ R.T * s + E).round(1).tolist() for d in D]

# frame: (turn, film eye midpoint, film eye-line angle in degrees, scale, why)
KEYS = {
 0:  (0.0, (171, 104), -12.0, 0.98, 'Start: head tilted up and a little to screen left, eyes half shut, tongue out; the held, swaying pose of the first four seconds.'),
 22: (0.0, (160, 97), -11.0, 0.98, 'Extreme of the slow sway: the head has drifted up and left, the highest point before it settles back.'),
 40: (0.03, (163, 108), -9.5, 1.0, 'Head dips lower and levels slightly: the start of the settle before the turn.'),
 47: (0.06, (170, 115), -9.0, 1.02, 'Anticipation: the last front-facing frame, chin tucked and head at its lowest before it swings round.'),
 48: (0.35, (186, 118), -11.0, 1.10, 'Breakdown inside the fast turn: the near eye has moved toward the middle, the far eye is closing on the brow edge, ears shifting.'),
 49: (0.72, (210, 130), -9.0, 1.18, 'Turn almost complete: three-quarter view facing screen right, muzzle now past the far eye, head lower and closer.'),
 51: (1.0, (243, 138), -2.0, 1.25, 'The line: the cat faces screen right in three-quarter view, ears up, eye on what is off screen right.'),
 55: (1.0, (266, 152), -6.0, 1.30, 'Settle: the head eases a little further right and down and stops.'),
 61: (1.0, (269, 148), -8.0, 1.32, 'Hold to the end, looking right; only a slight lift of the chin.'),
}

if __name__ == '__main__':
    for f, (t, E, a, s, why) in KEYS.items():
        p = HERE / f'k{f:03d}.json'
        old = json.load(open(p)) if p.exists() else {}
        json.dump({'why': why, 'strokes': place(t, np.array(E, float), a, s), 'extra': old.get('extra', {})}, open(p, 'w'))
    print('wrote', sorted(KEYS))
