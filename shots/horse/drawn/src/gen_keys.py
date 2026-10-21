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
 0: [(122, 178), (114, 154), (110, 128), (114, 106), (120, 94), (126, 88)],                       # cheek curve, left side
 1: [(120, 178), (128, 224), (140, 258), (152, 280), (180, 291), (208, 289), (228, 272), (244, 226),
     (252, 170), (244, 104), (198, 68), (134, 68), (60, 78), (-10, 92)],                            # face outline: long straight sides, blunt muzzle; then the crest going back behind the head
 2: [(120, 180), (55, 212), (-10, 248)],                                                          # throat
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


def neck_mane(K, Kd, k, back=0.0):
    """the mane (S7) and its end dot (S8): the doodle's one zigzag line, carried whole (rotated and scaled, not
    re-bent) so it keeps lying along the back of the neck from behind the poll. It is laid along the crest chord
    S1[11]->S1[13]; the doodle's mane drifts away from its crest toward the end (its crest bends), that drift is
    taken out so the line keeps hugging the neck and stays in the frame."""
    pd, cd = Kd[1][11], Kd[1][13]; ud = (cd - pd) / np.linalg.norm(cd - pd); vd = np.array([-ud[1], ud[0]])
    p, c = K[1][11], K[1][13]; u = (c - p) / np.linalg.norm(c - p); v = np.array([-u[1], u[0]])
    def carry(q):
        r = q - pd; al, nm = r @ ud, r @ vd
        nm = nm - max(al, 0) * 0.12          # take out the drift
        return p + (al * u + nm * v) * k + u * back
    K[7] = np.array([carry(q) for q in Kd[7]]); K[8] = np.array([carry(q) for q in Kd[8]])
    return K


def profile(P, N, wb=None, NT=(-10, 20), NB=(-10, 250), bulge=8, ref=None):
    P, N = np.array(P, float), np.array(N, float); L = np.linalg.norm(N - P); U = (N - P) / L; V = np.array([-U[1], U[0]])
    sa = L / L0; sb = wb or sa
    T = lambda q: P + ((q - Pd) @ U0) * sa * U + ((q - Pd) @ V0) * sb * V
    K = [np.array([T(q) for q in s]) for s in D]
    K = neck(K, NT, NB, bulge)
    th = np.degrees(np.arctan2(*(N - P)[::-1]))
    if ref:   # the ears stay pricked up (as in the film) instead of swinging forward as the face tips down
        for i in (4, 5):
            b = (K[i][0] + K[i][-1]) / 2; tip = K[i][np.argmax(np.linalg.norm(K[i] - b, axis=1))]
            r = np.radians(ref[i] + max(th - 60, 0) * 0.15 - np.degrees(np.arctan2(*(tip - b)[::-1])))
            R = np.array([[np.cos(r), -np.sin(r)], [np.sin(r), np.cos(r)]]); K[i] = (K[i] - b) @ R.T + b
    return neck_mane(K, D, (sa + sb) / 2)


PF, NF = np.array([185., 50.]), np.array([205., 292.])   # poll and muzzle of the front drawing (frame 0)


def neck(K, NT, NB, bulge=8):
    """crest S1[12..13] out to NT and throat S2[1..2] out to NB, the same way for every view, so they blend cleanly."""
    a, b = K[1][11], np.array(NT, float); nn = np.array([-(b - a)[1], (b - a)[0]]); nn /= np.linalg.norm(nn)
    if nn[1] > 0: nn = -nn
    K[1][12] = a + (b - a) * 0.4 + nn * bulge; K[1][13] = b
    a, b = K[2][0], np.array(NB, float); K[2][1] = a + (b - a) * 0.4; K[2][2] = b
    return K


def front(P, N, NT, NB, fw=1.0):
    """the front drawing carried onto the same poll P and muzzle N as the profile (so the two share one head axis
    and blend point for point): rotated and scaled, fw widens or narrows it across the axis."""
    P, N = np.array(P, float), np.array(N, float); u0 = (NF - PF) / np.linalg.norm(NF - PF); v0 = np.array([-u0[1], u0[0]])
    k = np.linalg.norm(N - P) / np.linalg.norm(NF - PF); u = (N - P) / np.linalg.norm(N - P); v = np.array([-u[1], u[0]])
    Tf = lambda q: P + ((q - PF) @ u0) * k * u + ((q - PF) @ v0) * k * fw * v
    K = [None] * 9
    for i, st in FRONT.items(): K[i] = np.array([Tf(q) for q in np.array(st, float)])
    K[3] = np.array([Tf(q) for q in scribble(EYE_L, 1.6)]); e2 = np.array([Tf(q) for q in scribble(EYE_R, 1.6)])
    K[3] = (K[3] - K[3].mean(0)) / k + K[3].mean(0); e2 = (e2 - e2.mean(0)) / k + e2.mean(0)   # eyes keep the doodle's size
    K = neck(K, NT, NB)
    K[7], K[8] = np.zeros((13, 2)), np.zeros((2, 2))
    return K, e2, k


# frame: (tau, front offset, P, N, width scale, NT, NB, why)
T = json.load(open(OUT / 'src/targets.json'))


def ear_ref():
    return {4: -105, 5: -70}   # ear directions in degrees (image axes, -90 = straight up): near ear up and back, far ear up and forward


def build(f):
    t = T[str(f)]; tau = t['tau']
    pr = profile(t['P'], t['N'], t.get('wb'), t['NT'], t['NB'], ref=ear_ref())
    extra = {}
    if tau < 1:
        fr, e2, kf = front(t['P'], t['N'], t['NT'], t['NB'], t.get('fw', 1.0))
        K = [fr[i] * (1 - tau) + pr[i] * tau for i in range(9)]
        K = neck(K, t['NT'], t['NB'])
        kp = np.linalg.norm(np.array(t['N'], float) - t['P']) / L0
        K = neck_mane(K, D, 1.3 * kf * (1 - tau) + kp * tau, 45 * kf * (1 - tau))
        if tau <= 0.75:
            # the far eye slides to the far edge of the face (the outline at eye level, S1[8]) and shrinks as the head
            # turns away; it is gone past three-quarter. On the way back to the front (eating) it comes out again.
            q = min(tau / 0.75, 1); edge = K[1][8] + (K[3].mean(0) - K[1][8]) * 0.08
            c = e2.mean(0) * (1 - q) + edge * q
            extra['eye2' if f < 20 else 'eye3'] = ((e2 - e2.mean(0)) * max(1 - q * q * 0.75, 0.35) + c).round(1).tolist()
    else:
        K = pr
    return {'why': t['why'], 'strokes': [s.round(1).tolist() for s in K], 'extra': extra}


if __name__ == '__main__':
    fs = [int(a) for a in sys.argv[1:]] or sorted(int(k) for k in T)
    for f in fs:
        json.dump(build(f), open(OUT / f'k{f:03d}.json', 'w'))
    print('wrote', fs)
