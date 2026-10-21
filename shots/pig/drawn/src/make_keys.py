"""Draw the pig's keys from the doodle itself (the frame-0 rig drawing, which is the doodle as rigged).
Every key is that drawing, placed by the film's snout position and a scale, with
  - the head turned from profile (t=0) to three-quarter (t=1): the doodle's own zigzag ears spread, the near ear
    grows, the far ear stays smaller and partly behind, the snout spiral ends about a third of the way across the head;
  - the body kept the doodle's flat-topped oval, shortened along its length as the pig turns, tipped up a little
    when the pig is close (the camera looks down on its back);
  - the legs swung about their tops in a walk cycle once the pig walks (front pair and hind pair opposite);
  - an extra "pole" stroke (the handler's catch-pole) held on the snout until the pig is let go.
Run from the repo root:  python3 shots/pig/drawn/src/make_keys.py"""
import json
import numpy as np
from pathlib import Path
D = Path('shots/pig/drawn'); G = Path('shots/pig-gwp')
rig = json.load(open(G / 'rig_frames.json'))
A = lambda x: np.array(x, float)

R0 = [A(s) for s in rig[0]]
SC = R0[1][6:].mean(0)                       # snout spiral centre in the doodle drawing
P = [s - SC for s in R0]                      # the doodle, snout at the origin
sp = P[1][6:]
# three-quarter head, same points and stroke meanings as the profile (S1 back of head > near ear > valley >
# far ear > forehead > into the spiral; S2 jaw, here also the near cheek; S4 points 7-9 chest up to the chin)
H3 = {
    1: np.r_[A([[64, -44], [60, -106], [38, -50], [14, -82], [-4, -40], [-2, -12]]), sp * 1.1],
    2: A([[10, 14], [20, 32], [40, 40], [62, 26], [72, -6]]),
    4: A([[66, 60], [40, 52], [22, 40]]),
}
PIV = A([70, -20])                            # the neck: the body is shortened and tipped about this point
POLE_TOP = A([-14, 48])                       # the far end of the catch-pole, fixed in the frame


def rot(v, deg, c):
    a = np.radians(deg); R = A([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]); return (v - c) @ R.T + c


def key(f, snout, k, t, tilt=0.0, brot=0.0, swing=0.0, bs=1.0, boff=(0, 0)):
    out = [s.copy() for s in P]
    # head: blend profile -> three-quarter, tilt about the middle of the head
    for i in (1, 2):
        out[i] = rot((1 - t) * P[i] + t * H3[i], tilt, A([25, -40]))
    tail = (1 - t) * P[4][7:] + t * H3[4]
    # body: shortened along its length, then tipped about the neck
    c = 1 - 0.3 * max(0.0, (t - 0.5) / 0.5)   # shorten only once the head is past half way
    def body(v):
        v = v.copy(); v[:, 0] = np.where(v[:, 0] > PIV[0], PIV[0] + (v[:, 0] - PIV[0]) * c, v[:, 0]); return rot(PIV + (v - PIV) * bs, brot, PIV)
    out[0] = body(P[0]); out[3] = body(P[3]); b4 = body(P[4][:7]); out[4] = np.r_[b4, rot(tail, tilt * 0.5, A([25, -40]))]
    out[3][0] = out[1][0] + A([5, 2])         # the back starts at the back of the head
    # legs: swing about their tops (front pair opposite each other, hind pair opposite), then follow the body
    sw = lambda s, a: rot(s, a, s[0])
    out[9] = sw(P[9], swing); out[8] = sw(P[8], -swing); out[7] = rot(P[7], -swing, P[8][0])
    out[5] = sw(P[5], -swing); out[6] = sw(P[6], swing)
    for i in (5, 6): out[i] = body(out[i])
    for i in (7, 8, 9): out[i] = rot(out[i], brot * 0.5, PIV)
    out = [A(snout) + s * k for s in out]
    # the body does not follow every move of the head: shift it (and the legs) by boff, keep the back joined to the head
    for i in (0, 3, 4, 5, 6, 7, 8, 9):
        if i == 4: out[4][:7] += A(boff)
        else: out[i] = out[i] + A(boff)
    out[3][0] = out[1][0] + A([5, 2]) * k
    # chest: in the turned view the belly runs straight up to the chin, no dip below the frame
    mid = 0.5 * (out[4][6] + out[4][8]) + A([0, 6]) * k
    out[4][7] = (1 - t) * out[4][7] + t * mid
    # front legs hang from the chest line, not across it
    for i in (7, 8, 9): out[i] = out[i] + t * A([10, 8]) * k
    return out


def pole(f, snout, k):
    end = A(snout) + A([-6, -4]) * k
    return np.array([POLE_TOP, POLE_TOP * 0.45 + end * 0.55 + A([0, 2]), end, end + A([7, 7]), end + A([2, 15]), end + A([-7, 10])])


def walk(f):  # leg swing in degrees: still until the pig walks, then one step every 3 frames
    return 0.0 if f < 10 else 9.0 * np.sin(2 * np.pi * (f - 10) / 6 + np.pi / 2)


# (frame, snout centre, scale, turn 0..1 (1 = three-quarter), head tilt, body tip, why)
KEYS = [
    (7, (78, 111), 1.0, 0.0, -2, 0, 'Still on the catch-pole, starting to pull: the head comes forward a little, the body still.'),
    (8, (92, 104), 1.0, 0.0, -6, 0, 'The pig pulls against the pole and lifts its head; still a side view, the start of the turn.'),
    (9, (112, 98), 1.0, 0.12, -12, 0, 'Anticipation, the last frame on the pole: head at its highest, tipped up and back, before it swings round.'),
    (10, (132, 108), 1.0, 0.32, -7, 0, 'Let go: the pole is gone and the head starts to swing toward the camera; the far ear shows. First step.'),
    (11, (142, 121), 1.0, 0.52, -2, 0, 'The ears spread, the near ear grows; the snout moves in from the edge of the head.'),
    (12, (141, 140), 1.0, 0.72, 1, -2, 'Turning on: the head drops toward the camera, the body begins to shorten.'),
    (13, (137, 152), 1.02, 0.88, 3, -4, 'Nearly round: snout a third of the way across the head.'),
    (14, (128, 166), 1.04, 1.0, 0, -6, 'THE LINE: the pig looks at the camera in three-quarter view, near ear large, far ear behind, body shortened behind the head.'),
    (15, (124, 174), 1.06, 1.0, 1, -9, 'A little air after the line: the same three-quarter head, one step closer.'),
    (16, (113, 184), 1.08, 1.0, 2, -11, 'Walking toward the camera: the head grows and comes down-left.'),
    (17, (100, 198), 1.1, 1.0, 1, -14, 'Walking toward us, the head lower.'),
    (18, (80, 208), 1.12, 1.0, 0, -17, 'Head low in the lower left, the body behind it tipped up toward the back of the pen.'),
    (19, (74, 218), 1.13, 1.0, 2, -18, 'Contact: a front foot lands and the head dips to its lowest point.'),
    (20, (80, 214), 1.15, 1.0, 1, -18, 'Recoil from the dip: the head starts back up.'),
    (21, (92, 199), 1.18, 1.0, -1, -18, 'The head lifts fast and comes closer (the film moves quickly here).'),
    (22, (98, 185), 1.2, 1.0, 0, -16, 'Head up and close: the top of the lift.'),
    (24, (88, 186), 1.22, 1.0, 0, -14, 'Close, three-quarter view, settling.'),
    (25, (88, 189), 1.22, 1.0, 0, -14, 'Last frame: close, three-quarter view.'),
]
BS = {12: 1.01, 13: 1.03, 14: 1.05, 15: 1.07, 16: 1.09, 17: 1.11, 18: 1.13, 19: 1.15, 20: 1.15, 21: 1.15, 22: 1.15, 24: 1.15, 25: 1.15}

BODY_UP = {11: -6, 12: -18, 13: -30, 14: -40, 15: -48, 16: -56}

if __name__ == '__main__':
    for p in D.glob('k[0-9][0-9][0-9].json'): p.unlink()
    # body position: near the rig's body while the pig stands and pulls (7-12), then a smoothed path of the head
    # so the head's dip and lift at 19-22 do not throw the whole body
    sns = {f: A(sn) for f, sn, *_ in KEYS}; fs = sorted(sns)
    W = {7: 1.0, 8: 1.0, 9: 1.0, 10: 0.7, 11: 0.4, 12: 0.15}
    BODY_AT = {7: (320, 110), 8: (334, 104), 9: (350, 96), 10: (364, 102), 11: (370, 114), 12: (362, 128),
               13: (352, 138), 14: (344, 148)}   # body centre (back and rump strokes) while the pig is let go and turns
    for f, sn, k, t, tilt, brot, why in KEYS:
        off = A([0, 0])
        if f in BODY_AT:
            st0 = key(f, sn, k, t, tilt, brot, walk(f), BS.get(f, 1.0))
            off = A(BODY_AT[f]) - np.concatenate([st0[0], st0[3][1:]]).mean(0)
        if f >= 17:
            near = [g for g in fs if abs(g - f) <= 2]
            off = off + (np.mean([sns[g] for g in near], 0) - A(sn)) * 0.8
        off = off + A([0, BODY_UP.get(f, -64 if f > 16 else 0)])   # the film's head is lowered: the back rides above it
        st = key(f, sn, k, t, tilt, brot, walk(f), BS.get(f, 1.0), off)
        ex = {}
        json.dump({'why': why, 'strokes': [np.round(s, 1).tolist() for s in st], 'extra': ex}, open(D / f'k{f:03d}.json', 'w'))
    # the catch-pole is scenery, not part of the pig: static poles in rigs/pig_scene.json, one per stretch of
    # frames, each ending on the snout where the snout is in those frames (written here so they match the keys)
    import json as _j
    sc = _j.load(open('rigs/pig_scene.json')); sc['objects'] = [o for o in sc['objects'] if not o['id'].startswith('catch_pole')]
    sn_rig = A(rig[3][1][6:]).mean(0)
    for name, vis, sn in (('catch_pole', [0, 6], sn_rig), ('catch_pole_7', [7, 7], A(KEYS[0][1])),
                          ('catch_pole_8', [8, 8], A(KEYS[1][1])), ('catch_pole_9', [9, 9], A(KEYS[2][1]))):
        q = pole(0, sn, 1.0)
        sc['objects'].append({'id': name, 'plane': 'char', 'class': 'line', 'visible': vis,
            'why': "the handler's catch-pole from the upper left to the pig's snout (no Quick, Draw! category is a catch-pole); "
                   "one copy per stretch of frames so its end stays on the snout until the pig is let go after frame 9",
            'strokes': [np.round(q[:3], 1).tolist(), np.round(q[2:], 1).tolist()]})
    _j.dump(sc, open('rigs/pig_scene.json', 'w'), indent=1)
    print('wrote', [k[0] for k in KEYS])
