"""Redraw the aircraft-carrier doodle for a new view of the ship.

The doodle is a slab drawn in its own oblique view: the top face (S0 stern edge + far long edge, S1 near long edge +
bow edge, S4 centre line), the near side face (S2 bottom of the near side, its last segment the near vertical corner
at the bow), and the bow end face (S3 its far vertical edge). Every doodle point is given ship coordinates
u (stern 0 -> bow 1), v (near/port side 0 -> far side 1), w (deck 0 -> keel 1) by undoing the doodle's own oblique
axes, so its wobbles and steps stay where the doodler put them. A key is then the same points seen by a pinhole
camera looking down at the ship with heading angle phi (0 = bow straight at the camera, positive = bow swung to
the camera's right, showing the port side on the left).

usage: python3 shots/aircraft-carrier/drawn/carrier_view.py   (writes k###.json for every frame in KEYS)
"""
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
D = json.load(open(ROOT / 'rigs/aircraft_carrier_spec.json'))['strokes']

# the doodle's own axes (doodle pixels): near stern deck corner, along the ship, across the deck, down the side
O = np.array([5., 74.]); A = np.array([214., -17.]); B = np.array([31., -45.]); H = np.array([4., 24.])
FIX = ['w', 'w', 'v', 'u', 'w']           # per stroke: which ship coordinate is known (deck strokes w=0, near side v=0, bow end u=1)


def ship_coords():
    out = []
    for s, fix in zip(D, FIX):
        pts = []
        for p in np.array(s, float):
            q = p - O
            if fix == 'w':
                u, v = np.linalg.solve(np.c_[A, B], q); w = 0.
            elif fix == 'v':
                u, w = np.linalg.solve(np.c_[A, H], q); v = 0.
            else:
                v, w = np.linalg.solve(np.c_[B, H], q - A); u = 1.
            pts.append((u, v, w))
        out.append(np.array(pts))
    return out


UVW = ship_coords()
UVW[0][0] = UVW[1][0].copy()              # S0 and S1 meet in one clean stern corner
# The doodle's hull runs under the deck to the bow. S2 (the underside of the near side, with its notch) is kept on
# the near side as drawn up to the notch and then led to the stem's foot under the middle of the bow; S3 (the bow
# end stroke) starts at the far bow corner on the deck and runs down to the same stem foot. Seen from ahead the two
# draw the V of the bow below the deck; seen from the side, the hull's underside running forward to the stem.
STEM = np.array([0.97, 0.5, 2.0])
UVW[2][4] = STEM; UVW[2][5] = STEM
UVW[2][0] = UVW[1][0] + np.array([0., 0., 0.45])   # the underside starts straight below the stern corner
UVW[0][3] = UVW[1][7].copy()                # S0 and S1 also meet in one clean far bow corner
UVW[3][0] = UVW[1][7].copy(); UVW[3][2] = STEM   # S3 starts from that corner
L, BEAM, DEPTH = 4.2, 1.1, 0.32            # ship size in world units (length, beam, depth of the hull per doodle unit)
PITCH = np.radians(8)                       # camera looks down at this angle
DIST = 30.0                                 # camera distance from the ship's centre


STRUCT = [[0, 1, 3], [0, 5, 7], [0, 1, 2, 3, 4, 5], [0, 1, 2], [0, 2]]   # per stroke: the corners that are placed in 3D
DOODLE = [np.array(s, float) for s in D]


def _sim(p0, p1, q0, q1, pts):
    """the similarity (rotate + scale + move, no mirror) taking p0->q0, p1->q1, applied to pts"""
    dp, dq = p1 - p0, q1 - q0
    a = complex(*dq) / complex(*dp) if np.hypot(*dp) > 1e-6 else 1
    z = ((pts[:, 0] - p0[0]) + 1j * (pts[:, 1] - p0[1])) * a
    return np.c_[z.real + q0[0], z.imag + q0[1]]


def project(phi_deg, cx, cy, scale):
    """phi: heading in degrees; (cx, cy): where the ship's deck centre lands in the frame; scale: pixels per unit.
    Only each stroke's corners (STRUCT) are placed in 3D. The doodle's points between two corners (the steps of
    S1, the hook and notch of S2, the bend of S4) are carried over as drawn, by the rotation and scaling that takes
    the doodle's segment onto the projected segment, so the steps stay small steps of the same edge in every view."""
    ph = np.radians(phi_deg)
    h = np.array([np.sin(ph), -np.cos(ph), 0.]); c = np.array([np.cos(ph), np.sin(ph), 0.])
    cam = np.array([0., -DIST * np.cos(PITCH), DIST * np.sin(PITCH)])
    fwd = -cam / np.linalg.norm(cam); right = np.array([1., 0, 0]); up = np.cross(right, fwd)
    res = []
    for s, d, st in zip(UVW, DOODLE, STRUCT):
        P = ((s[:, 0:1] - .5) * L * h + (s[:, 1:2] - .5) * BEAM * c + (s[:, 2:3]) * DEPTH * np.array([0, 0, -1.])) - cam
        z = P @ fwd; q = np.c_[cx + (P @ right) / z * DIST * scale, cy - (P @ up) / z * DIST * scale]
        out = q.copy()
        for i0, i1 in zip(st[:-1], st[1:]):
            out[i0:i1 + 1] = _sim(d[i0], d[i1], q[i0], q[i1], d[i0:i1 + 1])
        res.append(out)
    return res


BOW_NEAR, BOW_FAR = (1., 0., 0.), (1., 1.26, 0.)   # the two ends of the doodle's bow edge (S1's last segment)


def corners(phi):
    """image positions of the bow edge's two ends at scale 1 with the ship centre at the origin"""
    ph = np.radians(phi); h = np.array([np.sin(ph), -np.cos(ph), 0.]); c = np.array([np.cos(ph), np.sin(ph), 0.])
    cam = np.array([0., -DIST * np.cos(PITCH), DIST * np.sin(PITCH)])
    fwd = -cam / np.linalg.norm(cam); right = np.array([1., 0, 0]); up = np.cross(right, fwd)
    out = []
    for u, v, w in (BOW_NEAR, BOW_FAR):
        P = (u - .5) * L * h + (v - .5) * BEAM * c - cam; z = P @ fwd
        out.append(np.array([(P @ right) / z * DIST, -(P @ up) / z * DIST]))
    return out


def place(phi, flx, fly, width0):
    """phi: heading; (flx, fly): where the near end of the bow edge (the deck's front-left corner) lands;
    width0: how wide the bow edge would be in pixels if the ship were head on at this distance."""
    n0, f0 = corners(0.); sc = width0 / np.linalg.norm(f0 - n0)
    n, _ = corners(phi)
    return project(phi, flx - n[0] * sc, fly - n[1] * sc, sc)


def write(keys):
    for f, (phi, flx, fly, w0, why) in keys.items():
        strokes = place(phi, flx, fly, w0)
        p = HERE / f'k{f:03d}.json'
        old = json.load(open(p)) if p.exists() else {}
        json.dump({'why': why, 'strokes': [np.round(s, 1).tolist() for s in strokes], 'extra': old.get('extra', {})}, open(p, 'w'), indent=0)


if __name__ == '__main__':
    import sys
    keys = json.load(open(HERE / 'view_keys.json'))
    write({int(f): v for f, v in keys.items()})
    print('wrote', sorted(int(f) for f in keys))
