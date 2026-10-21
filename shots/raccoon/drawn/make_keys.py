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
    e0 = out[11]   # the doodle's own wide ear tab, same four turns, a little smaller
    ear = e0 + np.array([[6, -9], [3, -20], [-18, -24], [-26, -17]], float) * 0.8
    S[0] = np.vstack([out, ear])
    S[11] = ORIG[11] - centre(ORIG[11]) + [29, 40]           # eyes either side of the middle
    S[12] = ORIG[12] - centre(ORIG[12]) + [51, 40]
    m = ORIG[13] - centre(ORIG[13]); S[13] = m * [0.75, 1] + [40, 55]   # smile centred under them
    b = ORIG[1].copy(); bc = np.array([140., 34.])   # the doodle's own oval body seen end-on: foreshortened
    b[:, 0] = 94 + (b[:, 0] - bc[0]) * 0.5              # across, a little taller, sitting up behind the head
    b[:, 1] = 70 - (70 - b[:, 1]) * 1.12
    S[1] = b
    # tail tucked at the right side of the mound, small: only its tip shows
    tb = np.array(SP['anchors']['tailbase'], float)
    for i in range(2, 7): S[i] = rot((ORIG[i] - tb) * 0.36 + [124, 58], [124, 58], 30)
    S[7] = np.array([[30, 68], [27, 82], [33, 78]], float)    # front legs under the head, hooked foot kept
    S[8] = np.array([[50, 69], [51, 83]], float)
    S[9] = np.array([[88, 74], [87, 84]], float)              # hind legs barely show under the mound
    S[10] = np.array([[110, 71], [112, 82]], float)
    extra = np.array([[19, 25], [16, 14], [26, 15]], float)   # only the tip of the far ear, top left
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


def make(w, dip, s, H, head_scale=1.0, hump=30., G=None):
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
        e = (1 - k) * e + k * (S[0][13:16] + [-3, 2])
        ex['ear2'] = dipper(e)
    for i in head_parts(): S[i] = dipper(S[i])
    hc = S[0][:12].mean(0)
    place = lambda a: (np.array(a) - hc) * s + H
    out, exo = [place(x) for x in S], {k: place(v) for k, v in ex.items()}
    if G is not None:   # set the lowest point of the head (the snout) on the ground line G
        dy = G - out[0][:, 1].max(); out = [x + [0, dy] for x in out]; exo = {k: v + [0, dy] for k, v in exo.items()}
    return out, exo


KEYS = {
    0: dict(w=0.06, dip=-14, s=0.66, H=(219, 153), why='First frame: facing the camera, head low over the mud at the grass edge.'),
    1: dict(w=0.05, dip=-12, s=0.66, H=(221, 152), why='Facing the camera at the edge of the grass, head low over the mud: the face to us, the oval body seen end-on behind it.'),
    4: dict(w=0.0, dip=4, s=0.68, H=(222, 146), why='Head comes up and looks straight at the camera: the small anticipation before the turn.'),
    6: dict(w=0.1, dip=-10, s=0.67, H=(216, 150), why='Head starts down and the face begins to swing to screen left: the turn begins.'),
    8: dict(w=0.27, dip=-16, s=0.66, H=(207, 154), why='Turn under way: face a quarter to the left, head lower, body starting to lengthen.'),
    10: dict(w=0.46, dip=-24, s=0.65, H=(196, 158), why='Halfway through the turn: three-quarter left, head dropping toward the mud, body half stretched.'),
    12: dict(w=0.66, dip=-34, s=0.63, H=(186, 160), G=180, why='Three-quarter left, head low: the nose is nearly at the mud, body almost full length.'),
    14: dict(w=0.86, dip=-44, s=0.62, H=(178, 160), G=184, why='The line: near left profile, snout pointed down onto the mud, back hunched behind the head.'),
    16: dict(w=1.0, dip=-48, s=0.62, H=(182, 160), G=185, why='Profile complete: snout pressed into the mud, the turn settles.'),
    18: dict(w=1.0, dip=-42, s=0.63, H=(194, 160), G=185, why='Settle: still nose down, the body rounds and slides right as it shuffles.'),
    21: dict(w=1.0, dip=-22, s=0.65, H=(208, 158), G=176, why='Head lifts off the mud between pokes.'),
    23: dict(w=1.0, dip=-52, s=0.67, H=(220, 162), G=186, why='Pokes the mud again: snout straight down, hunch at its highest.'),
    27: dict(w=1.0, dip=-24, s=0.68, H=(222, 158), G=177, why='Lifts the head again to chew or look.'),
    31: dict(w=1.0, dip=-52, s=0.68, H=(223, 162), G=186, why='Snout back down into the mud.'),
    34: dict(w=1.0, dip=-40, s=0.68, H=(224, 162), G=184, why='Still nosing the mud at the end of the shot.'),
}

if __name__ == '__main__':
    for f, k in KEYS.items():
        st, ex = make(k['w'], k['dip'], k['s'], k['H'], k.get('head_scale', 1 - 0.12 * k['w']), k.get('hump', 30.), k.get('G'))
        json.dump({'why': k['why'], 'strokes': [np.round(x, 1).tolist() for x in st],
                   'extra': {n: np.round(v, 1).tolist() for n, v in ex.items()}}, open(D / f'k{f:03d}.json', 'w'))
    print('keys', sorted(KEYS))
