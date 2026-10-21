"""Builds the dog's drawn keys from the Quick, Draw! doodle's own strokes (rigs/dog_spec.json).

Each key is the same twelve strokes in one of three views, blended point by point:
  yaw 0  the doodle as drawn (left profile), head turned about the neck joint by `rot` degrees
  yaw 1  the same strokes redrawn facing the camera: muzzle loop and nostril in the middle at the bottom of
         the head, the eye diamond on one side and a second eye (extra stroke) on the other, the head-top
         and jaw lines become the two sides of the head, the front legs either side under it, the hind legs
         and the rear block small behind
  yaw 2  the doodle mirrored (right profile)
Coordinates are doodle units relative to the chest point (105, 77); `place` scales and moves them to the
frame. Usage: python3 gen.py [frame ...]  (writes k###.json next to this folder's parent).
"""
import json, math, sys
from pathlib import Path
import numpy as np
D = Path(__file__).resolve().parent.parent; ROOT = D.parent.parent.parent
SP = json.load(open(ROOT / 'rigs' / 'dog_spec.json'))
ST = [np.array(s, float) for s in SP['strokes']]
CH = np.array([105., 77.]); NECK = np.array([100., 47.]) - CH


def resample(s, n):
    s = np.array(s, float)
    if len(s) == n: return s
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(s, axis=0).T))]; t = np.linspace(0, d[-1], n)
    return np.c_[np.interp(t, d, s[:, 0]), np.interp(t, d, s[:, 1])]


HEAD = {0: range(0, 4), 2: range(5, 8), 3: None, 4: None, 5: None, 6: None}   # head vertices (None: whole stroke)
LEGTOP = {7: (156, 94), 8: (171, 97), 9: (198, 90), 10: (235, 92)}


def rotate(p, c, deg):
    a = math.radians(deg); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (p - c) @ R.T + c


def profile(rot=0.0, legs=None):
    """the doodle, chest at the origin; rot > 0 lifts the nose, < 0 drops it (left-facing)."""
    out = [s - CH for s in ST]
    for i, rg in HEAD.items():
        s = out[i].copy(); idx = list(rg) if rg is not None else list(range(len(s)))
        s[idx] = rotate(s[idx], NECK, rot); out[i] = s
    for i, a in (legs or {}).items():   # swing a leg about its top
        out[i] = rotate(out[i], np.array(LEGTOP[i], float) - CH, a)
    return out


def front(hy=0.0, rx=0.0):
    """the same strokes (same point counts) seen from the front, chest at the origin. hy: head centre height
    (+ is lower); rx: how far to the side the rear block shows past the head (the body runs back that way)."""
    o = [None] * 12; h = np.array([0.0, hy])
    hd = lambda a: np.array(a, float) * [1.15, 1.0] + h   # the face is a little wider than it is tall
    sh = min(hy + 14, -6.0)          # where the neck meets the shoulders
    back = -22.0                     # the top of the back, seen past the head
    # S0: from the nose over the left brow, across the top of the head, down the right cheek, neck, back
    o[0] = np.r_[hd([[0, 13], [-21, -4], [-9, -21], [14, -19], [25, -3], [15, 13]]), [[26, sh], [rx * 0.5 + 10, back + 4]]]
    # S2: belly hook, up the left side of the chest, throat, left jaw, to the nose
    o[2] = np.r_[[[-9, 26], [-3, 28], [-13, 22], [-22, 4], [-23, sh]], hd([[-24, 2], [-13, 15], [-3, 16]])]
    # S3 muzzle loop and S4 nostril at the bottom centre of the head
    o[3] = hd([[-8, 5], [-8, 14], [0, 18], [8, 14], [8, 4]])
    o[4] = hd([[-1, 9], [1, 11]])
    # S5 eye diamond and S6 pupil, narrowed, on the left of the face
    c5 = ST[5].mean(0)
    o[5] = hd((ST[5] - c5) * [0.42, 0.85] + [-11, -7]); o[6] = hd((ST[6] - c5) * [0.42, 0.85] + [-11, -7])
    # front legs either side under the chest, hind legs behind, outside them and shorter, x narrowed
    for i, (x, y, kx, ky) in {7: (-18, 22, -0.5, 0.95), 8: (17, 24, -0.5, 0.95), 9: (-30, 12, -0.5, 0.78), 10: (29, 12, -0.5, 0.78)}.items():
        o[i] = (ST[i] - LEGTOP[i]) * [kx, ky] + [x, y]
    # rear block and rump line: the far end of the body, showing past the head on the back
    c11 = ST[11].mean(0); o[11] = (ST[11] - c11) * [-0.5, 0.55] + [rx, c11[1] - CH[1] - 4]
    o[1] = (ST[1] - ST[1][0]) * [-0.3, 0.45] + [rx - 14, back + 8]
    return o


def front_extra(hy=0.0):
    c5 = ST[5].mean(0)
    return {'eye2': (ST[5] - c5) * [-0.42, 0.85] + [11, -7 + hy], 'pupil2': (ST[6] - c5) * [-0.42, 0.85] + [11, -7 + hy]}


def view(yaw, rot=0.0, hy=0.0, legs=None, rx=0.0, hyaw=None, extras=False):
    """yaw 0 left profile, 1 front, 2 right profile: a turntable. Each point has its profile x (along the body)
    and its front x (across the body); seen at angle th its x is px*cos(th) + fx*sin(th), and its height moves
    from the profile height to the front height as the front shows. hyaw: the head's own turn (a dog looks
    at us before its body has come round); default the body's."""
    hyaw = yaw if hyaw is None else hyaw
    F = front(hy, rx); P = profile(rot, legs)
    def ang(y):
        th = math.radians(90 * y); c, s = math.cos(th), math.sin(th); return c, s, s ** 3
    out = []
    for i, (p, f) in enumerate(zip(P, F)):
        hidx = set(range(len(p))) if HEAD.get(i, 0) is None else set(HEAD.get(i, []))
        q = np.zeros_like(p)
        for j in range(len(p)):
            c, s, wy = ang(hyaw if j in hidx else yaw)
            q[j] = [p[j, 0] * c + f[j, 0] * s, p[j, 1] * (1 - wy) + f[j, 1] * wy]
        out.append(q)
    c, s, wy = ang(hyaw)
    ex = {}
    w = min(1.0, max(0.0, (s - 0.6) / 0.3))   # second eye: only when the face is mostly toward us
    if extras:   # kept (shrunk to a point when w is 0) on every key of the turn so it never pops on or off
        for k, fe in front_extra(hy).items():
            pe = resample(P[5 if k == 'eye2' else 6], len(fe))
            q = np.c_[pe[:, 0] * c + fe[:, 0] * s, pe[:, 1] * (1 - wy) + fe[:, 1] * wy]
            m = q.mean(0); ex[k] = (q - m) * w + m
    return out, ex


def place(strokes, C, s, tilt=0.0):
    a = math.radians(tilt); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return [(st @ R.T) * s + C for st in strokes]


KEYS = json.load(open(Path(__file__).resolve().parent / 'keys.json'))

if __name__ == '__main__':
    fs = [int(a) for a in sys.argv[1:]] or [int(k) for k in KEYS]
    for f in fs:
        k = KEYS[str(f)]
        st, ex = view(k['yaw'], k.get('rot', 0), k.get('hy', 0), {int(i): v for i, v in k.get('legs', {}).items()}, k.get('rx', 0), k.get('hyaw'), k.get('extras', False))
        st = place(st, np.array(k['C'], float), k['s'], k.get('tilt', 0))
        ex = dict(zip(ex, place(list(ex.values()), np.array(k['C'], float), k['s'], k.get('tilt', 0))))
        J = {'why': k['why'], 'strokes': [np.round(s, 1).tolist() for s in st], 'extra': {n: np.round(s, 1).tolist() for n, s in ex.items()}}
        json.dump(J, open(D / f'k{f:03d}.json', 'w'))
        print('wrote', f'k{f:03d}.json')
