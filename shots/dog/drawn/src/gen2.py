"""Dog drawn keys, version 2 (after blind critic round 1): no full-front view.

Every key is the doodle's own side view (rigs/dog_spec.json strokes), never redrawn frontally:
  rot   the head turns about the neck joint (degrees; negative drops the snout). The head keeps its outline,
        almond eye and pointed snout at every angle.
  fb    the body foreshortens along its length (1 side-on, small = seen end-on as the dog turns toward us);
        the box stays a box and every leg stays hung from its own top on the box, keeping its own shape.
  face  -1 the doodle as drawn (facing left), +1 mirrored (facing right). The facing changes between two
        consecutive keys at the moment the snout points straight down and the body is end-on, so the
        mirror is nearly invisible.
Coordinates: doodle units about the chest point (105, 77), placed in the frame at C with scale s.
usage: python3 gen2.py  (writes ../k###.json for every key in keys2.json and removes keys not listed)
"""
import json, math
from pathlib import Path
import numpy as np
SRC = Path(__file__).resolve().parent; D = SRC.parent; ROOT = D.parent.parent.parent
ST = [np.array(s, float) for s in json.load(open(ROOT / 'rigs' / 'dog_spec.json'))['strokes']]
CH = np.array([105., 77.]); NECK = np.array([100., 47.]) - CH
HEAD = {0: range(0, 4), 2: range(5, 8), 3: None, 4: None, 5: None, 6: None}
LEGTOP = {7: (156, 94), 8: (171, 97), 9: (198, 90), 10: (235, 92)}


def rotate(p, c, deg):
    a = math.radians(deg); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (p - c) @ R.T + c


def key(rot, fb, face, hl=1.0):
    out = []
    for i, s in enumerate(ST):
        s = s - CH; hidx = set(range(len(s))) if HEAD.get(i, 0) is None else set(HEAD.get(i, []))
        q = s.copy()
        for j in range(len(s)):
            if j in hidx:   # head: turned about the neck, a little shorter when the snout comes toward us
                v = s[j] - NECK; q[j] = NECK + v * [hl, 1.0]
            else:           # body: foreshortened along its length
                q[j] = [s[j][0] * fb, s[j][1]]
        if i in LEGTOP:     # a leg keeps its own drawn shape, hung from its (foreshortened) top
            t = np.array(LEGTOP[i], float) - CH; q = s - t + [t[0] * fb, t[1]]
        idx = sorted(hidx)
        if idx: q[idx] = rotate(q[idx], NECK, rot)
        out.append(q * [-face, 1])
    return out


if __name__ == '__main__':
    K = json.load(open(SRC / 'keys2.json'))
    for p in D.glob('k[0-9][0-9][0-9].json'):
        if str(int(p.stem[1:])) not in K: p.unlink()
    for f, k in K.items():
        st = [s * k['s'] for s in key(k['rot'], k['fb'], k['face'], k.get('hl', 1.0))]
        if 'T' in k:   # T: where the middle of the drawing's bounding box goes (read off the film's dog)
            P = np.concatenate(st); off = np.array(k['T'], float) - (P.min(0) + P.max(0)) / 2
        else: off = np.array(k['C'], float)
        st = [s + off for s in st]
        json.dump({'why': k['why'], 'strokes': [np.round(s, 1).tolist() for s in st], 'extra': {}}, open(D / f'k{int(f):03d}.json', 'w'))
    print(len(K), 'keys')
