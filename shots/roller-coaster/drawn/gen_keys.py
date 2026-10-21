"""Generate drawn keys for roller-coaster: track moved so its peak sits on the film's crest, drop lines
redrawn at the doodle's own steep angle, and a train of open-box cars climbing the upper rail."""
import json, sys
import numpy as np
ROOT = '/home/claude/cartoon-archive'
SP = ROOT + '/shots/roller-coaster/drawn'
rig = json.load(open(f'{SP}/rig_before_keys.json'))

# doodle drop lines, relative to their own start
D17 = np.array([[191, 9], [231, 88], [255, 124]], float); D17 -= D17[0]
D18 = np.array([[146, 75], [169, 112], [234, 188]], float); D18 -= D18[0]
DOODLE_LIFT = np.hypot(192 - 0, 4 - 171)

# frame: (crest target for S0[0], front car arc distance below the top of S1, why)
T = {
    0:  ((190, 24), 56, 'the train is halfway up the lift and the camera starts tilting up; first key, the train low on the upper rail'),
    4:  ((181, 32), 49, 'the camera tilts up and the crest slides down-left; the train climbs'),
    8:  ((168, 46), 41, 'the tilt is fastest: the crest drops toward the middle of the frame; the train keeps climbing'),
    12: ((156, 58), 33, 'the tower is coming into view above the crest; the train climbs'),
    16: ((146, 70), 26, 'the tower is fully in view; the front car is a third of the way below the crest'),
    20: ((139, 79), 19, 'the camera settles; the train climbs steadily'),
    24: ((132, 88), 14, 'second, smaller tilt; the front car is close under the crest'),
    28: ((127, 92), 11, 'the framing steadies; the train slows as it nears the top'),
    32: ((124, 91), 8, 'framing steady; the train creeps up'),
    36: ((122, 90), 6, 'the front car is just under the crest, slowing'),
    40: ((121, 89), 4, 'anticipation: the front car waits just below the crest'),
    44: ((121, 89), 2, 'anticipation: the front car is almost level with the crest'),
    48: ((121, 89), -1, 'the line: the front car tops the crest under the tower and the riders come up over it'),
    52: ((121, 89), -4, 'after the line: the front car noses over onto the flat top, the rest of the train still on the lift'),
}
NCAR, L, GAP, H = 5, 14.0, 3.5, 8.0
LEAN = 27.0
LIFT, RIDER = 2.5, 6.0


def path_point(P, s):
    """P: polyline; s arc length from P[0]. Extrapolates before the start along the first segment."""
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    if s <= 0:
        t = (P[1] - P[0]) / d[1]; return P[0] + t * s, t
    i = min(np.searchsorted(d, s) - 1, len(P) - 2); i = max(i, 0)
    t = (P[i + 1] - P[i]) / (d[i + 1] - d[i]); return P[i] + t * (s - d[i]), t


def key(f):
    (cx, cy), front, why = T[f]
    R = [np.array(s, float) for s in rig[f]]
    sh = np.array([cx, cy]) - R[0][0]
    R = [s + sh for s in R]
    # lean the lift to the film's constant angle (about 27 degrees from vertical), pivoting on the crest
    c = R[1][0] - R[1][-1]; cur = np.degrees(np.arctan2(c[0], -c[1]))
    th = np.radians(LEAN - cur); piv = R[0][0].copy()
    rot = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    for i in list(range(0, 17)) + [18]:
        R[i] = (R[i] - piv) @ rot.T + piv
    scale = np.hypot(*(R[0][0] - R[0][-1])) / DOODLE_LIFT
    R[17] = R[0][0] + D17 * scale * 0.95
    R[18] = R[18][0] + D18 * scale * 0.95
    # upper rail from its top downward; before its top, the crest runs toward S0[0] (the flat top)
    S1 = R[1]
    P = np.vstack([S1[0] + (S1[0] - R[0][0]) * 0, S1])  # S1 from its top
    out = {}
    s = front
    for c in range(NCAR):
        if s < 0:   # over the top: run along the crest toward the drop
            u = (R[0][0] - S1[0]); u /= np.hypot(*u)
            a = S1[0] + u * (-s)
        else:
            a, _ = path_point(S1, s)
        s2 = s + L
        b, t = path_point(S1, s2) if s2 >= 0 else (S1[0] + (R[0][0] - S1[0]) / np.hypot(*(R[0][0] - S1[0])) * (-s2), None)
        v = b - a; v /= np.hypot(*v)
        n = np.array([v[1], -v[0]])   # away from the lower rail (up-left of a rising track)
        if np.dot(n, S1[len(S1) // 2] - R[0][len(R[0]) // 2]) < 0: n = -n
        a0, b0 = a + n * LIFT, b + n * LIFT
        box = [a0 + n * H, a0, b0, b0 + n * H, a0 + n * H]
        out[f'car{c + 1}'] = [[round(x, 1), round(y, 1)] for x, y in box]
        up = n + np.array([0, -1.0]); up /= np.hypot(*up)
        m = (a0 + b0) / 2 + n * H
        out[f'rider{c + 1}'] = [[round(x, 1), round(y, 1)] for x, y in (m, m + up * RIDER)]
        s = s2 + GAP
    return {'why': why, 'strokes': [[[round(x, 1), round(y, 1)] for x, y in s] for s in R], 'extra': out}


for f in T:
    json.dump(key(f), open(f'{ROOT}/shots/roller-coaster/drawn/k{f:03d}.json', 'w'), indent=0)
print('ok')
