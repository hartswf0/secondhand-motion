"""Assemble shot.json: one substance (planes, doodles, cast, camera, x-sheet) for the giraffe shot.
World coordinates = screen coordinates at frame 0 (480x360). A plane at depth z moves by cam * (Z_REF / z)."""
import os
QD = os.environ.get('QD_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'quickdraw'))
import json, math, random, sys
import numpy as np
sys.path.insert(0, '.')
from rig import draw

random.seed(4); rng = np.random.default_rng(4)
g = json.load(open('clip.json')); N = len(g['frames'])
cam = json.load(open('camera.json'))
cast = json.load(open('drawn_frames_v5.json'))
P = json.load(open('pose_agent_v5.json')); keys = sorted(int(k) for k in P)
Z_REF = 3.0

def qd(cat, ok, n, skip=0):
    out = []
    for l in open(f'{QD}/{cat}.part').read().splitlines()[:-1]:
        r = json.loads(l)
        if not r['recognized']: continue
        d = r['drawing']; xs = np.concatenate([s[0] for s in d]); ys = np.concatenate([s[1] for s in d])
        a = (xs.max() - xs.min() + 1) / (ys.max() - ys.min() + 1)
        if ok(a, d): out.append((r['key_id'], d))
    random.shuffle(out)
    return out[skip:skip + n]

def place(d, x, y, w, h=None, anchor='bottom'):
    xs = np.concatenate([s[0] for s in d]); ys = np.concatenate([s[1] for s in d])
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    sx = w / max(1, x1 - x0); sy = (h / max(1, y1 - y0)) if h else sx
    oy = y - (y1 - y0) * sy if anchor == 'bottom' else y
    return [[[round(x + (px - x0) * sx, 1), round(oy + (py - y0) * sy, 1)] for px, py in zip(s[0], s[1])] for s in d]

def wobble(strokes, seg=14, wob=2.0, seed=1):
    r = np.random.default_rng(seed); out = []
    for s in strokes:
        d = []
        for a, b in zip(s[:-1], s[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(1, int(L // seg))
            nx, ny = -(b[1] - a[1]) / (L or 1), (b[0] - a[0]) / (L or 1); bow = r.uniform(-1, 1) * wob
            for i in range(n):
                t = i / n; k = math.sin(math.pi * t) * bow
                d.append([round(a[0] + (b[0] - a[0]) * t + nx * k, 1), round(a[1] + (b[1] - a[1]) * t + ny * k, 1)])
        d.append(s[-1]); out.append(d)
    return out

objects = []
# PLANE sky (z=10): two real clouds
for i, (kid, d) in enumerate(qd('cloud', lambda a, d: a > 1.7 and len(d) <= 2, 2)):
    objects.append({'id': f'cloud{i+1}', 'plane': 'sky', 'z': 10, 'class': 'cloud', 'source': f'quickdraw:{kid}',
                    'strokes': place(d, [40, 400][i], [44, 30][i], 80)})
# PLANE far (z=6): treeline of real bushes
xs = np.arange(-140, 700, 70)
for i, (kid, d) in enumerate(qd('bush', lambda a, d: 1.5 < a < 3.2 and len(d) <= 3, len(xs))):
    w = float(rng.uniform(70, 95)); objects.append({'id': f'bush{i+1}', 'plane': 'far', 'z': 6, 'class': 'bush', 'source': f'quickdraw:{kid}',
        'strokes': place(d, float(xs[i] + rng.uniform(-12, 12)), float(176 + rng.uniform(-6, 6)), w)})
# PLANE mid (z=3): acacia drawn by the agent in Quick, Draw! idiom; right tree = best silhouette match
acacia = [[[248, 256], [247, 214], [246, 176], [244, 152]], [[262, 256], [262, 216], [263, 180], [266, 154]],
          [[244, 152], [222, 122], [200, 98], [172, 80], [146, 72], [112, 84]], [[200, 98], [190, 66], [184, 38]], [[172, 80], [160, 60]],
          [[250, 150], [242, 112], [234, 70], [226, 34], [240, 6]], [[234, 70], [212, 46], [206, 22]],
          [[256, 150], [266, 110], [276, 74], [290, 40], [296, 12]], [[276, 74], [306, 60], [330, 40]],
          [[266, 154], [292, 128], [318, 104], [342, 84], [348, 60]], [[318, 104], [340, 108]], [[292, 128], [306, 140]]]
objects.append({'id': 'acacia', 'plane': 'mid', 'z': 3, 'class': 'tree', 'source': 'drawn by agent as a bare thorn tree (no Quick, Draw! tree matched above 0.58 IoU)',
                'strokes': wobble(acacia, seed=11)})
m2 = json.load(open('match_tree2.json'))[0]
objects.append({'id': 'tree2', 'plane': 'mid', 'z': 3, 'class': 'tree', 'source': f"quickdraw:{m2['key_id']} (silhouette IoU {m2['iou']:.2f})",
                'strokes': place(m2['drawing'], 352, 264, 104, 222)})
# PLANE secondary (z=2.5): two young giraffes drawn with the adult's own rig at ~40% scale, so all three share one drawing convention
PRM = {"leg_w": 0, "seg": 10, "wobble": 1.5, "spots": 0, "ossicones": True, "tail": True, "bend": 3, "muzzle": 4, "tail_len": 16, "tuft": True}
base = P['16']
def all_pts(p):
    pts = [p[k] for k in ['head', 'nose', 'nb', 'chest', 'rump', 'tailroot', 'thigh', 'belly_f', 'belly_h']] + p['hooves'] + list(p.get('knees', {}).values())
    return np.array(pts, float)
A = all_pts(base); cx0 = (A[:, 0].min() + A[:, 0].max()) / 2; y1 = A[:, 1].max()
def small(cx, foot, s, mirror, look_up=0.0):
    def tf(q, k=None):
        x = (q[0] - cx0) * s * (-1 if mirror else 1) + cx; y = (q[1] - y1) * s + foot
        if k in ('head', 'nose'): y -= look_up
        return [x, y]
    p = {k: tf(base[k], k) for k in ['head', 'nose', 'nb', 'chest', 'rump', 'tailroot', 'thigh', 'belly_f', 'belly_h']}
    p['hooves'] = [tf(h) for h in base['hooves']]; p['knees'] = {k: tf(v) for k, v in base.get('knees', {}).items()}
    return p
def young_frames(cx, foot, s, mirror, look_at=None, seed=1):
    out = []
    for f in range(N):
        lu = 0.0
        if look_at is not None:
            t = min(1, max(0, (f - look_at) / 6)); lu = 6 * t * t * (3 - 2 * t)
        out.append(draw(small(cx, foot, s, mirror, lu), dict(PRM, seed=seed)))
    return out
objects.append({'id': 'young2', 'plane': 'secondary', 'z': 2.5, 'class': 'giraffe', 'source': "adult's rig at 38% scale, facing right",
                'frames': young_frames(366, 281, 0.38, False, None, 5)})
objects.append({'id': 'young1', 'plane': 'secondary', 'z': 2.5, 'class': 'giraffe', 'source': "adult's rig at 42% scale, facing the walker; lifts its head from frame 10",
                'frames': young_frames(290, 287, 0.42, True, 10, 6)})
# ground contact: a wavy ground line on the trees plane, grass tufts at the young giraffes' feet
gl = [[float(x), round(262 + 3 * math.sin(x / 37) + 2 * math.sin(x / 13), 1)] for x in range(-160, 680, 14)]
objects.append({'id': 'ground', 'plane': 'mid', 'z': 3, 'class': 'ground', 'source': 'drawn by agent', 'strokes': [gl]})
tufts = qd('grass', lambda a, d: a > 1.6 and len(d) <= 2, 1, skip=40)
for i, (kid, d) in enumerate(tufts):
    objects.append({'id': f'tuft{i+1}', 'plane': 'secondary', 'z': 2.5, 'class': 'grass', 'source': f'quickdraw:{kid}',
                    'strokes': place(d, 284, 291, 44)})
# PLANE fore (z=1.2): real grass doodles along the bottom
gx = np.arange(-300, 900, 62)
for i, (kid, d) in enumerate(qd('grass', lambda a, d: a > 2.0 and len(d) <= 3, len(gx))):
    objects.append({'id': f'grass{i+1}', 'plane': 'fore', 'z': 1.2, 'class': 'grass', 'source': f'quickdraw:{kid}',
                    'strokes': place(d, float(gx[i] + rng.uniform(-10, 10)), float(358 + rng.uniform(-6, 4)), float(rng.uniform(58, 78)))})

def ground_tick(st):
    pts = [q for s in st[:1] for q in s]; ymax = max(q[1] for q in pts)
    feet = [q[0] for q in pts if q[1] > ymax - 14]
    return [[round(min(feet) - 12, 1), round(ymax + 2, 1)], [round(max(feet) + 12, 1), round(ymax + 3, 1)]]

# x-sheet: keys from the agent pass, in-betweens interpolated, camera from footage
xsheet = []
for f in range(N):
    kind = 'K' if f in keys else 'B' if f % 2 == 0 else 'I'
    xsheet.append({'f': f, 'drawing': (f'K{keys.index(f)+1:02d}' if f in keys else f'{kind}{f:02d}'), 'kind': kind,
                   'cam': [round(cam[f][0], 1), round(cam[f][1], 1)],
                   'note': {0: 'walking right, head high', 4: 'front leg reaches back', 8: 'hind leg trails', 12: 'young giraffe turns head',
                            16: 'mid-stride, camera pan ends', 20: 'front legs spread', 24: 'hind leg steps forward', 28: 'hind leg kicks back', 32: 'turning toward camera'}.get(f, '')})

shot = {'title': 'Giraffe walks past', 'source': {'film': g['title'], 'url': g['url']}, 'fps': g['fps'], 'W': 480, 'H': 360, 'z_ref': Z_REF,
        'planes': [{'id': 'sky', 'z': 10, 'label': 'Sky'}, {'id': 'far', 'z': 6, 'label': 'Far treeline'}, {'id': 'mid', 'z': 3, 'label': 'Trees'},
                   {'id': 'secondary', 'z': 2.5, 'label': 'Young giraffes'}, {'id': 'char', 'z': 2, 'label': 'Walking giraffe'}, {'id': 'fore', 'z': 1.2, 'label': 'Grass'}],
        'camera': cam, 'objects': objects,
        'cast': {'id': 'giraffe', 'plane': 'char', 'frames': [f['strokes'] + [ground_tick(f['strokes'])] for f in cast], 'keys': keys},
        'xsheet': xsheet,
        'footage': [fr['im'] for fr in g['frames']], 'masks': [fr['p'] for fr in g['frames']]}
json.dump(shot, open('shot.json', 'w'), separators=(',', ':'))
print('objects', len(objects), 'by plane', {p: sum(1 for o in objects if o['plane'] == p) for p in ['sky', 'far', 'mid', 'secondary', 'fore']})
