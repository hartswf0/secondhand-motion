"""Draw the pig's turn keys: the doodle's own head strokes placed in profile (t=0) or front view (t=1)
at the film's snout position, blended for the three-quarter keys. Run from the repo root:
    python3 shots/pig/drawn/src/make_keys.py
Writes shots/pig/drawn/kFFF.json for every key in KEYS (body strokes start from the rig drawing)."""
import json
import numpy as np
from pathlib import Path
D = Path('shots/pig/drawn'); G = Path('shots/pig-gwp')
S = json.load(open(G / 'shot.json'))
rig = json.load(open(G / 'rig_frames.json')) if (G / 'rig_frames.json').exists() else S['cast']['frames']
A = lambda x: np.array(x, float)

# profile template: the frame-0 rig drawing (the doodle as rigged), relative to the snout spiral centre
R0 = [A(s) for s in rig[0]]
SC = A([65.0, 113.0])
P = [s - SC for s in R0]
sp = R0[1][6:] - SC
# front template, snout centre at origin, same point order and stroke meaning as the profile:
# S1 back of head -> ear -> valley -> ear -> forehead -> cheek into the snout spiral
# S2 jaw: under the snout, round the chin and up the far cheek
# S4 tail (points 7-9): chest under the head up to the near shoulder
# S7/S8 one front leg (upper slant + lower), S9 the other front leg
F = {
    1: np.r_[A([[50, -52], [58, -108], [0, -70], [-58, -108], [-62, -34], [-22, -8]]), sp * 1.3],
    2: A([[18, 40], [42, 34], [60, 10], [64, -18], [56, -46]]),
    4: A([[14, 50], [-34, 42], [-60, -20]]),
    7: A([[-48, 84], [-46, 108]]),
    8: A([[-40, 46], [-48, 90]]),
    9: A([[42, 46], [46, 80], [44, 108]]),
}
BODY = [(0, None), (3, slice(1, None)), (4, slice(0, 7)), (5, None), (6, None)]

def rot(v, deg, c):
    a = np.radians(deg); R = A([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]); return (v - c) @ R.T + c

def key(f, snout, k, t, tilt=0.0, legs=1.0, body=None, lift=0.0):
    r = [A(s) for s in rig[f]]; sn = A(snout)
    dx = A([sn[0] - r[1][6:].mean(0)[0], 0])   # the front of the pig follows the head sideways
    for i in (7, 8, 9): r[i] = r[i] + dx
    r[4][6:8] = r[4][6:8] + dx * [[0.5], [1.0]]
    out = [s.copy() for s in r]
    def place(loc):   # head-local offsets -> frame
        return sn + rot(loc * k, tilt, A([25, -40]) * k)
    # head strokes: blend profile and front templates
    out[1] = place((1 - t) * P[1] + t * F[1])
    out[2] = place((1 - t) * P[2] + t * F[2])
    # S4 tail and front legs: profile part follows the rig body, front part hangs under the head
    # front view: the body is mostly hidden behind the head, so it is drawn shorter toward the head
    hx = sn[0] + 55 * k; c = 1 - 0.3 * t
    for si, sl in BODY:
        q = out[si][sl] if sl else out[si]
        q[:, 0] = np.where(q[:, 0] > hx, hx + (q[:, 0] - hx) * c, q[:, 0])
    tail_p = np.r_[out[4][7:8], place(P[4][8:])]; tail_f = place(F[4])
    tail_p[1] = 0.5 * (tail_p[0] + tail_p[2]) + A([6, 4]) * k   # chest: smooth from the rig's chest to the chin
    out[4][7:] = (1 - t) * tail_p + t * tail_f
    for i in (7, 8, 9):
        lp = r[i]; lf = place(F[i]); out[i] = (1 - t * legs) * lp + t * legs * lf
    # back line starts at the back of the head
    out[3][0] = out[1][0] + A([5, 2]) * k
    if lift:   # the film's back is higher than the rig's while the pig walks at us
        out[3][2:] = out[3][2:] - A([0, lift]) * np.linspace(1, 0.4, len(out[3]) - 2)[:, None]
        out[0][:3] = out[0][:3] - A([0, lift * 0.4])
    # back line: from behind the far ear, rounded up into the back (no tent at the shoulder)
    out[3][0] = out[1][0] + A([5, 2]) * k
    out[3][1] = (1 - t) * out[3][1] + t * (0.5 * out[3][0] + 0.5 * out[3][2] + A([-8, -14]) * k)
    if body:
        for (si, pi), xy in body.items(): out[si][pi] = A(xy)
    return out

# (frame, snout centre, scale, turn, tilt, why, body overrides)
KEYS = [
    (8, (92, 104), 1.0, 0.0, -6, 'The catch-pole lets go and the pig lifts its head; still a side view, the start of the turn.', None),
    (9, (112, 94), 1.0, 0.12, -12, 'Anticipation: the head is at its highest, tipped up and back, before it swings round toward the camera.', None),
    (10, (132, 108), 1.0, 0.27, -7, 'The head starts to swing: the far ear begins to show and the snout moves off the edge of the head.', None),
    (11, (142, 121), 0.99, 0.4, -2, 'Three-quarter head: the far ear is up, the snout a third of the way to the middle.', None),
    (12, (141, 140), 0.97, 0.6, 1, 'Past half way: the ears are spreading to either side and the head drops toward the camera.', None),
    (13, (137, 152), 0.95, 0.82, 3, 'Nearly front-on: the snout is almost in the middle of the face.', None),
    (14, (128, 166), 0.95, 1.0, 0, 'THE LINE: the pig faces the camera; snout spiral in the middle of a round head, one ear either side.', None),
    (15, (124, 174), 0.96, 1.0, 1, 'A little air after the line: the same front face, a step closer.', None),
    (16, (113, 184), 0.97, 1.0, 2, 'First step toward the camera: the front head grows and comes down-left.', None),
    (17, (100, 198), 0.99, 1.0, 1, 'Walking toward us, the head lower.', None),
    (18, (80, 208), 1.0, 1.0, 0, 'Walking toward us, head low in the lower left, the body behind it.', None),
    (19, (74, 218), 1.01, 1.0, 2, 'Contact: a front foot lands and the head dips to its lowest point, down and left.', None),
    (20, (80, 214), 1.03, 1.0, 1, 'Recoil from the dip: the head starts back up.', None),
    (21, (92, 199), 1.06, 1.0, -1, 'The head lifts fast and comes closer to the camera (the film moves quickly here).', None),
    (22, (98, 185), 1.08, 1.0, 0, 'Head up and close: the top of the lift.', None),
    (24, (88, 186), 1.1, 1.0, 0, 'Close, front view, head in the lower left; settling.', None),
    (25, (88, 189), 1.1, 1.0, 0, 'Last frame: held front view, close.', None),
]

LIFT = {15: 8, 16: 14, 17: 20, 18: 26, 19: 26, 20: 26, 21: 20, 22: 10}

if __name__ == '__main__':
    for f, sn, k, t, tilt, why, body in KEYS:
        st = key(f, sn, k, t, tilt, body=body, lift=LIFT.get(f, 0.0))
        p = D / f'k{f:03d}.json'
        old = json.load(open(p)) if p.exists() else {}
        json.dump({'why': why, 'strokes': [np.round(s, 1).tolist() for s in st], 'extra': old.get('extra', {})}, open(p, 'w'))
    print('wrote', [k[0] for k in KEYS])
