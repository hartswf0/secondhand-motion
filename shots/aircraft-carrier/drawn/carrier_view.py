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
L, BEAM, DEPTH = 4.0, 1.25, 0.28           # ship size in world units (length, beam, deck-to-gallery depth)
PITCH = np.radians(10)                      # camera looks down at this angle
DIST = 14.0                                 # camera distance from the ship's centre


def project(phi_deg, cx, cy, scale):
    """phi: heading in degrees; (cx, cy): where the ship's deck centre lands in the frame; scale: pixels per unit."""
    ph = np.radians(phi_deg)
    h = np.array([np.sin(ph), -np.cos(ph), 0.]); c = np.array([np.cos(ph), np.sin(ph), 0.])
    cam = np.array([0., -DIST * np.cos(PITCH), DIST * np.sin(PITCH)])
    fwd = -cam / np.linalg.norm(cam); right = np.array([1., 0, 0]); up = np.cross(right, fwd)
    res = []
    for s in UVW:
        P = ((s[:, 0:1] - .5) * L * h + (s[:, 1:2] - .5) * BEAM * c + (s[:, 2:3]) * DEPTH * np.array([0, 0, -1.])) - cam
        z = P @ fwd; x = (P @ right) / z * DIST; y = -(P @ up) / z * DIST
        res.append(np.c_[cx + x * scale, cy + y * scale])
    return res


# frame: (phi, cx, cy, scale, why)
KEYS = {}


def write(keys):
    for f, (phi, cx, cy, sc, why) in keys.items():
        strokes = project(phi, cx, cy, sc)
        p = HERE / f'k{f:03d}.json'
        old = json.load(open(p)) if p.exists() else {}
        json.dump({'why': why, 'strokes': [np.round(s, 1).tolist() for s in strokes], 'extra': old.get('extra', {})}, open(p, 'w'), indent=0)


if __name__ == '__main__':
    import sys
    keys = json.load(open(HERE / 'view_keys.json'))
    write({int(f): v for f, v in keys.items()})
    print('wrote', sorted(int(f) for f in keys))
