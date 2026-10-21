"""Builds the raccoon's drawn keys k###.json from the doodle's own strokes (rigs/raccoon_spec.json).

Two poses are built in doodle units: FRONT (head turned to the camera, face centred, the doodle's ear on the
right of the head and an added second ear on the left, the body a mound behind the head) and FORAGE (the doodle's
left profile hunched: back raised, legs short, tail hanging, head turned down so the nose meets the ground).
A key is a blend of the two (0 = front, 1 = forage) plus a head dip, placed in the frame by its head centre.
Run from the repo root: python3 shots/raccoon/drawn/make_keys.py
"""
import json, math
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
D = Path(__file__).resolve().parent
SP = json.load(open(ROOT / 'rigs' / 'raccoon_spec.json'))
ORIG = [np.array(s, float) for s in SP['strokes']]


def rot(p, c, deg):
    a = math.radians(deg); c = np.array(c, float); q = np.array(p, float) - c
    return c + q @ np.array([[math.cos(a), math.sin(a)], [-math.sin(a), math.cos(a)]])


def centre(s): return np.array(s, float).mean(0)


# ---------- FRONT pose (doodle units) ----------
def front():
    S = [s.copy() for s in ORIG]
    hc = np.array([40., 44.]); rx, ry = 30., 27.
    o = ORIG[0]; oc = np.array([45., 40.])
    out = []
    for p in o[:12]:   # the head outline, each point moved to the same angle on a rounder, centred outline
        a = math.atan2(p[1] - oc[1], p[0] - oc[0])
        out.append(hc + [rx * math.cos(a), ry * math.sin(a)])
    out = np.array(out)
    # the doodle's ear tab, now upright on the top right of the head (same four turns as the doodle's tab)
    out[11] = hc + [rx * math.cos(math.radians(-42)), ry * math.sin(math.radians(-42))]   # end the outline high on the right
    e0 = out[11]
    ear = np.array([e0 + [2, -13], e0 + [-3, -23], e0 + [-13, -19], e0 + [-14, -9]])
    S[0] = np.vstack([out, ear])
    S[11] = ORIG[11] - centre(ORIG[11]) + [29, 40]           # eyes either side of the middle
    S[12] = ORIG[12] - centre(ORIG[12]) + [51, 40]
    m = ORIG[13] - centre(ORIG[13]); S[13] = m * [0.75, 1] + [40, 55]   # smile centred under them
    S[1] = np.array([[64, 22], [67, 4], [79, -12], [98, -18], [116, -12], [128, 4], [134, 30],
                     [132, 56], [122, 74], [100, 82], [80, 82], [68, 76], [64, 68]], float)
    # tail tucked at the right side of the mound, small: only its tip shows
    tb = np.array(SP['anchors']['tailbase'], float)
    for i in range(2, 7): S[i] = rot((ORIG[i] - tb) * 0.36 + [128, 66], [128, 66], 30)
    S[7] = np.array([[30, 68], [27, 82], [33, 78]], float)    # front legs under the head, hooked foot kept
    S[8] = np.array([[50, 69], [51, 83]], float)
    S[9] = np.array([[94, 80], [93, 86]], float)              # hind legs barely show under the mound
    S[10] = np.array([[114, 77], [116, 85]], float)
    extra = np.array([[e0[0] - 2 * (e0[0] - hc[0]), e0[1]]] + [[2 * hc[0] - q[0], q[1]] for q in ear[:3]])
    return S, {'ear2': extra}


# ---------- FORAGE pose (doodle units) ----------
def forage(hump=30.):
    S = [s.copy() for s in ORIG]
    neck = np.array(SP['anchors']['neck'], float)
    b = ORIG[1].copy()   # body: back raised into a hunch, most at the middle of the back, little at the belly
    t = np.clip((b[:, 0] - 62) / 155, 0, 1)
    lift = hump * np.sin(math.pi * t) ** 0.8 * (1 - np.clip(b[:, 1] / 70, 0, 1)) + 4
    b[:, 1] -= lift; b[:, 1] += np.where(b[:, 0] > 190, (b[:, 0] - 190) * 0.35, 0)   # rump drops
    S[1] = b
    tb = np.array(SP['anchors']['tailbase'], float); tnew = tb + [0, 6]
    for i in range(2, 7): S[i] = rot(ORIG[i], tb, 35) - tb + tnew    # tail hangs from the dropped rump
    for i, top in ((7, 'ftop'), (8, 'ftop'), (9, 'htop'), (10, 'htop')):   # legs folded: short strokes under the belly
        s = ORIG[i].copy(); s0 = s[0].copy(); S[i] = s0 + (s - s0) * 0.45 + [0, -2]
    for i in [1, 2, 3, 4, 5, 6, 9, 10]:   # hunched: the body bunches up toward the head
        S[i][:, 0] = neck[0] + (S[i][:, 0] - neck[0]) * 0.97
    return S, {}


def head_parts(): return [0, 11, 12, 13]


def blend(A, B, w):
    (SA, XA), (SB, XB) = A, B
    S = [SA[i] * (1 - w) + SB[i] * w for i in range(len(SA))]
    return S


def make(w, dip, s, H, head_scale=1.0, hump=30.):
    F, FX = front(); P, _ = forage(hump)
    S = blend((F, FX), (P, {}), w)
    hc = S[0][:12].mean(0)
    neck = (1 - w) * np.array([66., 50.]) + w * np.array([72., 42.])
    c0 = rot(neck + (S[0][:12].mean(0) - neck) * head_scale, neck, dip * w)
    def dipper(x):   # head dip (negative = nose down): in profile a turn about the neck, face-on a drop and a
        x = neck + (x - neck) * head_scale    # vertical squash (the top of the head shows more)
        x = rot(x, neck, dip * w)
        c = c0; sq = 1 + min(dip, 0) / 90 * (1 - w)
        return (x - c) * [1, sq] + c + [0, -dip * 0.5 * (1 - w)]
    ex = {}
    if w < 0.8:   # the second ear: on the left of the head face-on, sliding behind the doodle's own ear as it turns
        e = FX['ear2'] - F[0][:12].mean(0) + S[0][:12].mean(0)
        k = float(np.clip((w - 0.2) / 0.55, 0, 1)); k = k * k * (3 - 2 * k)
        e = (1 - k) * e + k * (S[0][12:16] + [-3, 2])
        ex['ear2'] = dipper(e)
    for i in head_parts(): S[i] = dipper(S[i])
    hc = S[0][:12].mean(0)
    place = lambda a: (np.array(a) - hc) * s + H
    return [place(x) for x in S], {k: place(v) for k, v in ex.items()}


KEYS = {
    0: dict(w=0.1, dip=-14, s=0.66, H=(219, 153), why='First frame: facing the camera, head low over the mud at the grass edge.'),
    1: dict(w=0.08, dip=-12, s=0.66, H=(221, 152), why='Facing the camera at the edge of the grass, head low over the mud: the face is to us, the body a mound behind it.'),
    4: dict(w=0.0, dip=4, s=0.68, H=(222, 146), why='Head comes up and looks straight at the camera: the small anticipation before the turn.'),
    8: dict(w=0.35, dip=-10, s=0.66, H=(208, 152), why='Turn starts: the face swings to screen left and the head begins to drop, second ear folding behind.'),
    12: dict(w=0.75, dip=-22, s=0.62, H=(186, 158), why='Three-quarter left, head low: the turn is nearly done and the nose is going to the mud.'),
    14: dict(w=1.0, dip=-26, s=0.6, H=(178, 158), why='The line: left profile, nose down on the mud, back hunched up behind the head.'),
    18: dict(w=1.0, dip=-22, s=0.62, H=(194, 158), why='Settle after the line: still nose down, the body rounds and slides right as it shuffles.'),
    23: dict(w=1.0, dip=-28, s=0.68, H=(222, 161), why='Foraging: nose pushed into the mud, hunch at its highest.'),
    29: dict(w=1.0, dip=-17, s=0.68, H=(223, 157), why='Small lift of the head between pokes at the mud.'),
    34: dict(w=1.0, dip=-27, s=0.68, H=(224, 161), why='Nose back down in the mud: the foraging continues to the end of the shot.'),
}

if __name__ == '__main__':
    for f, k in KEYS.items():
        st, ex = make(k['w'], k['dip'], k['s'], k['H'], k.get('head_scale', 0.9 if k['w'] > 0.5 else 1.0), k.get('hump', 30.))
        json.dump({'why': k['why'], 'strokes': [np.round(x, 1).tolist() for x in st],
                   'extra': {n: np.round(v, 1).tolist() for n, v in ex.items()}}, open(D / f'k{f:03d}.json', 'w'))
    print('keys', sorted(KEYS))
