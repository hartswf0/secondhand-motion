"""Generates the drawn keys for horse from the Quick, Draw! doodle 4658862839824384 (rigs/horse_spec.json).
Profile keys: the doodle mirrored to face right, its head placed by poll P and nose N (length along the head,
a separate width scale for foreshortening), its neck re-aimed to the neck ends NT (crest) and NB (throat).
Front keys: the same strokes redrawn for a front view by hand (FRONT below). Turn keys blend the two by tau.
usage: python3 shots/horse/drawn/src/gen_keys.py [frames...]"""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'shots/horse/drawn'
spec = json.load(open(ROOT / 'rigs/horse_spec.json'))
D = [np.array(s, float) for s in spec['strokes']]
D = [np.c_[255 - s[:, 0], s[:, 1]] for s in D]          # mirror: face right
Pd, Nd = np.array([125., 28.]), np.array([247., 118.])
L0 = np.linalg.norm(Nd - Pd); U0 = (Nd - Pd) / L0; V0 = np.array([-U0[1], U0[0]])
HEAD = {0: 'all', 1: range(0, 12), 2: [0], 3: 'all', 4: 'all', 5: 'all', 6: 'all'}

# front view (frame 0 coordinates), same stroke order and point counts as the doodle
FRONT = {
 0: [(122, 178), (112, 152), (108, 126), (112, 106), (120, 93), (128, 86)],                       # cheek curve, left side
 1: [(120, 178), (126, 222), (140, 260), (160, 284), (188, 290), (214, 280), (234, 248), (248, 198),
     (252, 145), (244, 98), (218, 66), (175, 54), (110, 52), (-10, 34)],                            # face outline, then neck crest
 2: [(120, 180), (55, 210), (-10, 245)],                                                          # throat
 4: [(150, 58), (132, 45), (114, 32), (100, 24), (112, 42), (136, 64)],                            # left ear (the doodle's back ear)
 5: [(214, 58), (228, 48), (246, 40), (257, 40), (255, 48), (240, 62), (228, 72)],                 # right ear (front ear)
 6: [(214, 64), (200, 52), (184, 47), (166, 48), (152, 52), (142, 58)],                            # line across the top between the ears
}
EYE_L, EYE_R = np.array([142., 158.]), np.array([228., 166.])


def scribble(c, k, n=None):
    s = D[3] - D[3].mean(0)
    if n: s = s[np.linspace(0, len(s) - 1, n).astype(int)]
    return s * k + c


def polyfit(Q):
    seg = np.diff(Q, axis=0); ln = np.hypot(*seg.T); return seg, ln, np.r_[0, np.cumsum(ln)]


def param(m, Q):
    """position of m relative to polyline Q: (arc fraction, normal offset); before the start: negative fraction."""
    seg, ln, cum = polyfit(Q); best = None
    for i in range(len(seg)):
        u = seg[i] / ln[i]; v = np.array([-u[1], u[0]]); a = (m - Q[i]) @ u
        a2 = a if i == 0 else max(a, 0); a2 = a2 if i == len(seg) - 1 else min(a2, ln[i])
        p = Q[i] + u * a2; d = np.linalg.norm(m - p)
        if best is None or d < best[0]: best = (d, (cum[i] + a2) / cum[-1], (m - Q[i] - u * a2) @ v)
    return best[1], best[2]


def place(s, n, Q, k):
    seg, ln, cum = polyfit(Q); t = s * cum[-1]
    i = 0 if t < 0 else min(np.searchsorted(cum, t, 'right') - 1, len(seg) - 1)
    u = seg[i] / ln[i]; v = np.array([-u[1], u[0]])
    return Q[i] + u * (t - cum[i]) + v * n * k


def neck_mane(K, Kd, k):
    """mane (S7) and its end dot (S8) follow the crest S1[11..13] the way they follow it in the doodle."""
    Qd, Q = Kd[1][11:14], K[1][11:14]
    K[7] = np.array([place(*param(m, Qd), Q, k) for m in Kd[7]])
    K[8] = K[7][-1] + (Kd[8] - Kd[7][-1]) * k
    return K


def profile(P, N, wb=None, NT=(-10, 20), NB=(-10, 250), bulge=8, ref=None):
    P, N = np.array(P, float), np.array(N, float); L = np.linalg.norm(N - P); U = (N - P) / L; V = np.array([-U[1], U[0]])
    sa = L / L0; sb = wb or sa
    T = lambda q: P + ((q - Pd) @ U0) * sa * U + ((q - Pd) @ V0) * sb * V
    K = [np.array([T(q) for q in s]) for s in D]
    a, b = K[1][11], np.array(NT, float); m = (a + b) / 2; nn = np.array([-(b - a)[1], (b - a)[0]]); nn /= np.linalg.norm(nn)
    if nn[1] > 0: nn = -nn
    K[1][12] = a + (b - a) * 0.4 + nn * bulge; K[1][13] = b
    a, b = K[2][0], np.array(NB, float); K[2][1] = a + (b - a) * 0.4; K[2][2] = b
    th = np.degrees(np.arctan2(*(N - P)[::-1]))
    if ref:   # the ears stay pricked up (as in the film) instead of swinging forward as the face tips down
        for i in (4, 5):
            b = (K[i][0] + K[i][-1]) / 2; tip = K[i][np.argmax(np.linalg.norm(K[i] - b, axis=1))]
            r = np.radians(ref[i] + max(th - 60, 0) * 0.15 - np.degrees(np.arctan2(*(tip - b)[::-1])))
            R = np.array([[np.cos(r), -np.sin(r)], [np.sin(r), np.cos(r)]]); K[i] = (K[i] - b) @ R.T + b
    return neck_mane(K, D, (sa + sb) / 2)


def front(off):
    off = np.array(off, float); K = [None] * 9
    for i, s in FRONT.items(): K[i] = np.array(s, float) + off
    K[3] = scribble(EYE_L + off, 1.6)
    K = neck_mane(K, D, 1.6)
    return K, scribble(EYE_R + off, 1.6, 6)


# frame: (tau, front offset, P, N, width scale, NT, NB, why)
T = json.load(open(OUT / 'src/targets.json'))


def ear_ref():
    return {4: -105, 5: -70}   # ear directions in degrees (image axes, -90 = straight up): near ear up and back, far ear up and forward


def build(f):
    t = T[str(f)]; tau = t['tau']
    pr = profile(t['P'], t['N'], t.get('wb'), t['NT'], t['NB'], ref=ear_ref())
    extra = {}
    if tau < 1:
        fr, e2 = front(t['off'])
        K = [fr[i] * (1 - tau) + pr[i] * tau for i in range(9)]
        # the far eye slides behind the nose bridge (toward S1[8]) and shrinks as the head turns
        hid = pr[1][8] - (pr[1][8] - pr[3].mean(0)) * 0.15
        c = e2.mean(0) * (1 - tau) + hid * tau
        extra['eye2'] = ((e2 - e2.mean(0)) * (1 - tau) ** 1.5 + c).round(1).tolist()
    else:
        K = pr
        # the far eye stays hidden behind the nose line for the rest of the shot (a tiny mark on the outline)
        hid = pr[1][8]; e = scribble(np.zeros(2), 0.08, 6); extra['eye2'] = (e + hid).round(1).tolist()
    return {'why': t['why'], 'strokes': [s.round(1).tolist() for s in K], 'extra': extra}


if __name__ == '__main__':
    fs = [int(a) for a in sys.argv[1:]] or sorted(int(k) for k in T)
    for f in fs:
        json.dump(build(f), open(OUT / f'k{f:03d}.json', 'w'))
    print('wrote', fs)
