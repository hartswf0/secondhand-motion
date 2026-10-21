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
    1: np.r_[A([[72, -84], [86, -114], [42, -92], [6, -134], [-12, -78], [-16, -18]]), sp * 1.2],
    2: A([[-8, 22], [6, 34], [26, 34], [50, 18], [72, -22]]),
    4: A([[96, 48], [66, 66], [36, 54], [22, 36]]),
    7: A([[56, 96], [58, 126]]),
    8: A([[64, 60], [54, 102]]),
    9: A([[102, 54], [108, 88], [102, 124]]),
}
YAW = A([[0, 0]])

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
    tail_p = np.r_[out[4][6:8], place(P[4][8:])]; tail_f = place(F[4])
    tail_p[2] = 0.5 * (tail_p[1] + tail_p[3]) + A([6, 4]) * k   # chest: smooth from the rig's chest to the chin
    out[4][6:] = (1 - t) * tail_p + t * tail_f
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
    (8, (92, 104), 1.0, 0.0, -6, 'The pig lifts its head and the camera starts to follow it right; still a profile, the start of the turn.', None),
    (9, (112, 94), 1.0, 0.08, -12, 'Anticipation: the head is at its highest, tipped up and back, before it swings round toward the camera.', None),
    (11, (142, 120), 0.95, 0.45, -2, 'Half way round: three-quarter head, the far ear coming into view and the snout swinging to the middle.', None),
    (13, (136, 152), 0.9, 0.85, 4, 'Nearly front-on: the snout is in the middle of the face and the head drops toward the camera.', None),
    (14, (128, 166), 0.9, 1.0, 0, 'THE LINE: the pig faces the camera; both ears either side of the head, snout in the middle.', None),
    (16, (113, 183), 0.97, 1.0, 2, 'First step toward the camera: the front head grows and comes down-left.', None),
    (18, (78, 209), 1.0, 1.0, 0, 'Walking toward us, head low in the lower left, the body angled away behind it.', None),
    (19, (73, 219), 1.0, 1.0, 2, 'Contact: a front foot lands and the head dips to its lowest point, down and left.', None),
    (20, (80, 214), 1.04, 1.0, 1, 'Recoil from the dip: the head starts back up.', None),
    (21, (93, 198), 1.1, 1.0, -1, 'The head lifts fast and comes closer to the camera (the film moves quickly here).', None),
    (22, (99, 183), 1.16, 1.0, 0, 'Head up and close: the top of the lift.', None),
    (24, (86, 184), 1.22, 1.0, 0, 'Close, front view, head in the lower left; settling.', None),
    (25, (87, 189), 1.22, 1.0, 0, 'Last frame: held front view, close.', None),
]

LIFT = {16: 14, 18: 26, 19: 26, 20: 26, 21: 20, 22: 10}

if __name__ == '__main__':
    for f, sn, k, t, tilt, why, body in KEYS:
        st = key(f, sn, k, t, tilt, body=body, lift=LIFT.get(f, 0.0))
        p = D / f'k{f:03d}.json'
        old = json.load(open(p)) if p.exists() else {}
        json.dump({'why': why, 'strokes': [np.round(s, 1).tolist() for s in st], 'extra': old.get('extra', {})}, open(p, 'w'))
    print('wrote', [k[0] for k in KEYS])
