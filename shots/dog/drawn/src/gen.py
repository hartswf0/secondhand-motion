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
    """the same strokes seen from the front. hy: head centre height (chest = 0, + is lower), rx: which side the
    body runs off behind (+ right, - left)."""
    h = np.array([0.0, hy]); ry = -40.0
    o = [None] * 12
    neck_top = max(-28.0, hy - 6)
    # S0: from the nose over the left brow, across the top of the head, down the right cheek, neck and back
    o[0] = np.array([[0, 14], [-15, -2], [-5, -19], [13, -15], [22, 2], [20, 18], [0, 0], [0, 0]], float) + [0, hy]
    o[0][6] = [24, (hy + 18 + neck_top) / 2 + 8]; o[0][7] = [rx * 0.7 + 14, ry + 10]
    # S2: belly hook, up the left side of the chest, throat, left jaw, to the nose
    o[2] = np.array([[-6, 24], [0, 27], [-9, 21], [-16, 4], [-17, min(hy + 20, -2)], [-18, hy + 8], [-10, hy + 17], [-2, hy + 16]], float)
    # S3 muzzle loop and S4 nostril at the bottom centre of the head
    o[3] = np.array([[-7, 7], [-7, 16], [0, 20], [7, 16], [7, 6]], float) + h
    o[4] = np.array([[-1, 11], [1, 13]], float) + h
    # S5 eye diamond and S6 pupil, narrowed, on the left of the face
    e = ST[5] - ST[5].mean(0); o[5] = e * [0.38, 0.85] + [-9, -5] + h
    p = ST[6] - ST[5].mean(0); o[6] = p * [0.38, 0.85] + [-9, -5] + h
    # front legs either side under the chest, hind legs behind and shorter, x narrowed (feet toward us)
    for i, (x, y, kx, ky) in {7: (-11, 20, 0.5, 1.0), 8: (11, 22, 0.5, 1.0), 9: (-21, 8, 0.4, 0.82), 10: (21, 8, 0.4, 0.82)}.items():
        s = ST[i] - LEGTOP[i]; o[i] = s * [kx, ky] + [x, y]
    # rear block and rump line, small, behind and above the shoulders, toward the side the body runs off
    c11 = ST[11].mean(0); o[11] = (ST[11] - c11) * [0.42, 0.55] + [rx, ry]
    o[1] = (ST[1] - ST[1][0]) * [0.3, 0.45] + [rx * 0.7 + 14, ry + 10]
    return o


def front_extra(hy=0.0):
    e = ST[5] - ST[5].mean(0); p = ST[6] - ST[5].mean(0)
    return {'eye2': (e * [-0.38, 0.85] + [9, -5 + hy]), 'pupil2': (p * [-0.38, 0.85] + [9, -5 + hy])}


def view(yaw, rot=0.0, hy=0.0, legs=None):
    rx = 16 * (1 - yaw)
    F = front(hy, rx); P = profile(rot, legs)
    if yaw <= 1: A, B, t = P, F, yaw
    else: A, B, t = F, [s * [-1, 1] for s in P], yaw - 1
    out = []
    for a, b in zip(A, B):
        n = max(len(a), len(b)); out.append(resample(a, n) * (1 - t) + resample(b, n) * t)
    ex = {}
    w = max(0.0, 1 - abs(yaw - 1) / 0.45)   # second eye: full at the front view, shrinks to a point by yaw 0.55 / 1.45
    if w > 0:
        for k, s in front_extra(hy).items():
            c = s.mean(0); s2 = (s - c) * w + c
            if yaw < 1: s2 = s2 + [ (1 - w) * 6, 0]
            else: s2 = s2 - [(1 - w) * 6, 0]
            ex[k] = s2
    return out, ex


def place(strokes, C, s, tilt=0.0):
    a = math.radians(tilt); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return [(st @ R.T) * s + C for st in strokes]


KEYS = json.load(open(Path(__file__).resolve().parent / 'keys.json'))

if __name__ == '__main__':
    fs = [int(a) for a in sys.argv[1:]] or [int(k) for k in KEYS]
    for f in fs:
        k = KEYS[str(f)]
        st, ex = view(k['yaw'], k.get('rot', 0), k.get('hy', 0), {int(i): v for i, v in k.get('legs', {}).items()})
        st = place(st, np.array(k['C'], float), k['s'], k.get('tilt', 0))
        ex = dict(zip(ex, place(list(ex.values()), np.array(k['C'], float), k['s'], k.get('tilt', 0))))
        J = {'why': k['why'], 'strokes': [np.round(s, 1).tolist() for s in st], 'extra': {n: np.round(s, 1).tolist() for n, s in ex.items()}}
        json.dump(J, open(D / f'k{f:03d}.json', 'w'))
        print('wrote', f'k{f:03d}.json')
