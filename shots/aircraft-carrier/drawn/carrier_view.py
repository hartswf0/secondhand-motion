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
# the doubled stern corner: in the doodle S0 starts a few pixels from S1's start; undoing the short oblique axis
# spreads that gap across a fifth of the beam, so put S0's first point back next to S1's first point
UVW[0][0] = UVW[1][0] + np.array([-0.02, 0.05, 0.])
L, BEAM, DEPTH = 3.3, 1.25, 0.28           # ship size in world units (length, beam, deck-to-gallery depth)
PITCH = np.radians(10)                      # camera looks down at this angle
DIST = 30.0                                 # camera distance from the ship's centre


def project(phi_deg, cx, cy, scale):
    """phi: heading in degrees; (cx, cy): where the ship's deck centre lands in the frame; scale: pixels per unit."""
    ph = np.radians(phi_deg)
    h = np.array([np.sin(ph), -np.cos(ph), 0.]); c = np.array([np.cos(ph), np.sin(ph), 0.])
    cam = np.array([0., -DIST * np.cos(PITCH), DIST * np.sin(PITCH)])
    fwd = -cam / np.linalg.norm(cam); right = np.array([1., 0, 0]); up = np.cross(right, fwd)
    res = []
    # the near side face (S2) is edge on or turned away while the bow points at the camera: only its front end shows,
    # and more of it slides into view as the bow swings right (fully out by 25 degrees)
    t = min(max(phi_deg / 25., 0.), 1.); g = 0.12 + 0.88 * t * t * (3 - 2 * t)
    for i, s in enumerate(UVW):
        if i == 2:
            s = s.copy(); s[:, 0] = 1 - (1 - s[:, 0]) * g
        P = ((s[:, 0:1] - .5) * L * h + (s[:, 1:2] - .5) * BEAM * c + (s[:, 2:3]) * DEPTH * np.array([0, 0, -1.])) - cam
        z = P @ fwd; x = (P @ right) / z * DIST; y = -(P @ up) / z * DIST
        res.append(np.c_[cx + x * scale, cy + y * scale])
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
