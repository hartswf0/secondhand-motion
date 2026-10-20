"""Puppet a real Quick, Draw! doodle through an archive shot: the manual redraw, done the giraffe way.

The chosen doodle keeps every one of its own strokes. The agent places a few joints on it (design
coordinates) and, for each key, says where those joints are in the footage (frame coordinates).
Each bone maps its two joints from the doodle onto the footage with a similarity transform (move,
turn, scale; never shear), and every doodle point follows the bones it is bound to (linear blend
skinning). In-betweens interpolate the joints; contact joints that barely move stay planted.

usage: python3 tools/puppet.py <category> [--sheet]
reads  shots/<cat>-redraw/rig.json, clip.json, frames/, the batch design and the traced look-lane key 0
writes shots/<cat>-redraw/shot.json (projector schema), cast.json, keys.png (keys over footage),
       inbetweens.png (a strip of every second frame)

rig.json:
  joints   {name: [x, y]}            on the doodle, 0-255 design units
  bones    {name: [joint_a, joint_b]}
  bind     {stroke_index: [bone, ...]} optional; unlisted strokes bind to the nearest bone
  contacts [joint, ...]              joints that can plant (feet, wheels on the ground)
  flip     true                      mirror the doodle (it faces the other way from the subject); a key may
                                     override with "_flip": true/false, and the swap happens mid in-between
  derive   {joint: bone}             joint placed by that bone instead of by hand (hips ride on the body)
  keys     [{joint: [x, y]}, ...]    one per key frame in clip.json, frame pixels
  notes    [str, ...]                what happens at each key (the x-sheet)
  camera   "static" | "measured"     static: the background plate never moves
"""
import json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / 'batches/2026-10-20-selected-drawings'


def seg_dist(p, a, b):
    ab = b - a; t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-9), 0, 1)
    return np.hypot(*(p - (a + np.outer(t, ab))).T)


def similarity(a, b, a2, b2):
    v, w = b - a, b2 - a2
    s = math.hypot(*w) / max(math.hypot(*v), 1e-9); r = math.atan2(w[1], w[0]) - math.atan2(v[1], v[0])
    M = s * np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
    return lambda P: (P - a) @ M.T + a2


def load(cat):
    d = ROOT / 'shots' / f'{cat}-redraw'
    rig = json.load(open(d / 'rig.json')); clip = json.load(open(d / 'clip.json'))
    des = json.load(open(B / 'subjects' / cat / 'design.json'))
    strokes = [np.c_[s[0], s[1]].astype(float) for s in des['drawing']]
    return d, rig, clip, des, strokes


def mirrored(rig, strokes):
    r = dict(rig); r['joints'] = {k: [255 - v[0], v[1]] for k, v in rig['joints'].items()}
    return r, [np.c_[255 - s[:, 0], s[:, 1]] for s in strokes]


def flip_of(rig, i):
    return rig['keys'][i].get('_flip', rig.get('flip', False))


def complete(rig, J, target):
    """Fill derived joints (e.g. hips) from the hand-placed bone that carries them."""
    t = {k: v for k, v in target.items() if not k.startswith('_')}
    for j, bone in rig.get('derive', {}).items():
        a, c = rig['bones'][bone]
        t[j] = similarity(J[a], J[c], np.array(t[a], float), np.array(t[c], float))(J[j][None])[0].tolist()
    return t


def weights(rig, strokes):
    J = {k: np.array(v, float) for k, v in rig['joints'].items()}
    bones = list(rig['bones']); W = []
    for i, s in enumerate(strokes):
        allowed = rig.get('bind', {}).get(str(i))
        D = np.stack([seg_dist(s, J[rig['bones'][b][0]], J[rig['bones'][b][1]]) for b in bones], 1)
        if allowed: D[:, [bones.index(b) for b in bones if b not in allowed]] = 1e6
        else:  # nearest bone for the stroke as a whole
            k = int(np.argmin(D.mean(0))); D[:, [j for j in range(len(bones)) if j != k]] = 1e6
        w = np.exp(-((D - D.min(1, keepdims=True)) / 10.0) ** 2); w[D >= 1e6] = 0
        W.append(w / w.sum(1, keepdims=True))
    return J, bones, W


def pose(rig, J, bones, W, strokes, target):
    target = complete(rig, J, target)
    T = {b: similarity(J[a], J[c], np.array(target[a], float), np.array(target[c], float)) for b, (a, c) in rig['bones'].items()}
    out = []
    for s, w in zip(strokes, W):
        P = sum(w[:, [k]] * T[b](s) for k, b in enumerate(bones))
        out.append(P)
    return out


def tween_joints(rig, clip, cam):
    """Per-frame joint positions: Catmull-Rom through the keys; planted contacts hold in world space."""
    keys, K = clip['keys'], rig['keys']; n = clip['n']; names = [j for j in rig['joints'] if j not in rig.get('derive', {})]
    world = lambda p, f: np.array(p, float) - np.array(cam[f])          # screen -> world; cam[f] is how far still things moved on screen
    frames = []; planted = []
    for f in range(n):
        if f <= keys[0]: frames.append({j: K[0][j] for j in names}); planted.append(set()); continue
        if f >= keys[-1]: frames.append({j: K[-1][j] for j in names}); planted.append(set()); continue
        a = max(i for i, k in enumerate(keys) if k <= f); b = a + 1
        t = (f - keys[a]) / (keys[b] - keys[a]); te = t * t * (3 - 2 * t)
        p0, p3 = K[max(0, a - 1)], K[min(len(K) - 1, b + 1)]
        fr = {}; pl = set()
        for j in names:
            A, Bp = np.array(K[a][j], float), np.array(K[b][j], float)
            if j in rig.get('contacts', []):
                wa, wb = world(K[a][j], keys[a]), world(K[b][j], keys[b])
                if np.hypot(*(wb - wa)) < 10:       # planted: same spot in the world, then a quick settle
                    w = wa if t < 0.85 else wa + (wb - wa) * ((t - 0.85) / 0.15)
                    fr[j] = (w + np.array(cam[f])).tolist(); pl.add(j) if t < 0.85 else None; continue
                lift = math.sin(math.pi * t) * min(12, 0.3 * np.hypot(*(wb - wa)))
                P = A + (Bp - A) * te; fr[j] = [P[0], P[1] - lift]; continue
            P0, P3 = np.array(p0[j], float), np.array(p3[j], float)
            c = 0.5 * ((2 * A) + (-P0 + Bp) * t + (2 * P0 - 5 * A + 4 * Bp - P3) * t * t + (-P0 + 3 * A - 3 * Bp + P3) * t ** 3)
            fr[j] = c.tolist()
        frames.append(fr); planted.append(pl)
    return frames, planted


def plate(cat, clip, key0_char, W, H):
    """Background drawn once: the look-lane key 0 traced, minus the character region and specks."""
    from scipy.spatial import ConvexHull
    from matplotlib.path import Path as MPath
    tr = json.load(open(ROOT / 'traced/traced_keys.json'))[cat]['keys'][0]['strokes']
    pts = np.concatenate(key0_char); hull = pts[ConvexHull(pts).vertices]
    c = hull.mean(0); hull = c + (hull - c) * 1.18 + np.sign(hull - c) * 10
    poly = MPath(hull); out = []
    for s in tr:
        a = np.array(s, float)
        if len(a) < 2 or np.hypot(*np.diff(a, axis=0).T).sum() < 10: continue
        if poly.contains_points(a).mean() > 0.3: continue
        out.append(a)
    return out


def main(cat, sheet=True):
    d, rig, clip, des, strokes = load(cat)
    # keys: the look-lane key frames, plus any extra key the agent added with "_f" (e.g. the middle of a turn)
    look = clip['keys']; it = iter(look); frames = []
    for k in rig['keys']: frames.append(k['_f'] if '_f' in k else next(it))
    order = sorted(range(len(frames)), key=lambda i: frames[i])
    rig['keys'] = [rig['keys'][i] for i in order]; rig['notes'] = [rig.get('notes', [''] * len(frames))[i] if i < len(rig.get('notes', [])) else '' for i in order]
    clip = dict(clip, keys=[frames[i] for i in order], look_keys=look)
    cam = json.load(open(d / 'camera.json')) if rig.get('camera') == 'measured' else [[0.0, 0.0]] * clip['n']
    rigs = {False: (rig, strokes), True: mirrored(rig, strokes)}
    rigged = {fl: (r, st) + weights(r, st) for fl, (r, st) in rigs.items()}
    jf, planted = tween_joints(rig, clip, cam)
    keys = clip['keys']; cast = []; flips = []
    for f, fr in enumerate(jf):
        a = max([i for i, k in enumerate(keys) if k <= f] or [0]); b = min(a + 1, len(keys) - 1)
        mid = keys[a] + (keys[b] - keys[a]) / 2
        fl = flip_of(rig, a) if f < mid or a == b else flip_of(rig, b); flips.append(fl)
        r, st, J, bones, W = rigged[fl]
        cast.append([np.round(p, 1).tolist() for p in pose(r, J, bones, W, st, fr)])
    jf = [complete(rigged[fl][0], rigged[fl][2], fr) for fl, fr in zip(flips, jf)]
    key0 = [np.array(s) for s in cast[clip['keys'][0]]]
    bg = plate(cat, clip, key0, clip['W'], clip['H'])
    shot = {'title': rig.get('title', cat.capitalize()), 'category': cat, 'fps': clip['fps'], 'W': clip['W'], 'H': clip['H'], 'z_ref': 3,
            'planes': [{'id': 'set', 'z': 3, 'label': 'Background, drawn once'}, {'id': 'char', 'z': 2, 'label': cat.capitalize()}],
            'camera': [[c[0], c[1]] for c in cam],
            'objects': [{'id': 'plate', 'plane': 'set', 'z': 3, 'class': 'ground', 'source': 'look-lane key 0 traced, character region removed',
                         'strokes': [np.round(s, 1).tolist() for s in bg]}],
            'cast': {'frames': cast, 'keys': clip['keys'], 'look_keys': clip['look_keys'], 'source': f"quickdraw:{des['key_id']} (the chosen doodle, every stroke kept)"},
            'joints': jf, 'planted': [sorted(p) for p in planted],
            'xsheet': [{'f': f, 'kind': 'K' if f in clip['keys'] else 'B', 'note': (rig['notes'][clip['keys'].index(f)] if f in clip['keys'] else '')} for f in range(clip['n'])],
            'footage': [f'frames/f{f:03d}.jpg' for f in range(clip['n'])], 'masks': [[] for _ in range(clip['n'])],
            'design': {'key_id': des['key_id'], 'strokes': len(des['drawing'])}}
    (d / 'shot.json').write_text(json.dumps(shot, separators=(',', ':')))
    if sheet: sheets(d, clip, cast, bg, jf)
    print(cat, 'frames', clip['n'], 'strokes', len(strokes), 'plate strokes', len(bg))


def draw_frame(img, strokes, bg, S=1, col=(22, 20, 18)):
    g = ImageDraw.Draw(img)
    for s in bg: g.line([(x * S, y * S) for x, y in s], fill=(150, 145, 138), width=max(1, int(S)))
    for s in strokes:
        pts = [(x * S, y * S) for x, y in s]
        if len(pts) > 1: g.line(pts, fill=(255, 255, 255), width=int(6 * S));
    for s in strokes:
        pts = [(x * S, y * S) for x, y in s]
        if len(pts) > 1: g.line(pts, fill=col, width=int(2.5 * S), joint='curve')
        else: g.ellipse([pts[0][0] - 2, pts[0][1] - 2, pts[0][0] + 2, pts[0][1] + 2], fill=col)


def sheets(d, clip, cast, bg, jf, S=1.5):
    W, H = clip['W'], clip['H']; tiles = []
    for i, k in enumerate(clip['keys']):
        im = Image.open(d / 'frames' / f'f{k:03d}.jpg').convert('RGB'); im = Image.blend(im, Image.new('RGB', im.size, 'white'), 0.35).resize((int(W * S), int(H * S)))
        draw_frame(im, cast[k], [], S, col=(220, 60, 0)); g = ImageDraw.Draw(im)
        for j, p in jf[k].items(): g.ellipse([p[0] * S - 3, p[1] * S - 3, p[0] * S + 3, p[1] * S + 3], outline=(0, 90, 220), width=2); g.text((p[0] * S + 4, p[1] * S - 10), j, fill=(0, 60, 180))
        g.rectangle([0, 0, 90, 14], fill='white'); g.text((3, 1), f'key {i} f{k}', fill='black'); tiles.append(im)
    w, h = tiles[0].size; sh = Image.new('RGB', (2 * w, 2 * h), 'white')
    for i, t in enumerate(tiles): sh.paste(t, ((i % 2) * w, (i // 2) * h))
    sh.save(d / 'keys.png')
    step = max(1, clip['n'] // 12); fr = list(range(0, clip['n'], step))[:12]; tw, th = W // 2, H // 2
    strip = Image.new('RGB', (4 * tw, 3 * th), 'white')
    for n, f in enumerate(fr):
        t = Image.new('RGB', (W, H), 'white'); draw_frame(t, cast[f], bg); g = ImageDraw.Draw(t); g.text((4, 2), f'f{f}', fill=(120, 120, 120))
        strip.paste(t.resize((tw, th)), ((n % 4) * tw, (n // 4) * th))
    strip.save(d / 'inbetweens.png')


if __name__ == '__main__':
    main(sys.argv[1])
