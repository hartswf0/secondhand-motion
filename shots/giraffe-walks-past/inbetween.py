"""Keyframe poses -> per-frame poses -> strokes for every frame of the clip.
Body follows eased interpolation plus the SAM mask centroid residual; hooves step in arcs."""
import json, math, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, '.')
from rig import draw

g = json.load(open('clip.json')); P = json.load(open(sys.argv[1])); prm = json.loads(sys.argv[2])
W, H = g['W'], g['H']; N = len(g['frames'])
keys = sorted(int(k) for k in P)
BODY = ['head', 'nose', 'nb', 'chest', 'rump', 'tailroot', 'thigh', 'belly_f', 'belly_h']

def centroid(f):
    m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
    for p in f['p']: d.polygon([tuple(q) for q in p], fill=255)
    a = np.array(m) > 0; ys, xs = np.nonzero(a)
    return np.array([xs.mean(), ys.mean()]) if len(xs) else None

cents = [centroid(f) for f in g['frames']]
ease = lambda t: t * t * (3 - 2 * t)

def knee_default(pose, i):
    face = 1 if pose['nose'][0] >= pose['rump'][0] else -1
    nf = 2  # front legs are the first two hooves
    chest, belly_f, belly_h = pose['chest'], pose['belly_f'], pose['belly_h']
    thigh = pose.get('thigh', pose['rump'])
    if i < nf: a = [chest[0] + (belly_f[0] - chest[0]) * (0.25 + 0.5 * i), chest[1] + (belly_f[1] - chest[1]) * (0.25 + 0.5 * i)]
    else:
        j = i - nf; a = [belly_h[0] + (thigh[0] - belly_h[0]) * (0.25 + 0.5 * j), belly_h[1] + (thigh[1] - belly_h[1]) * (0.25 + 0.5 * j)]
    h = pose['hooves'][i]; b = prm.get('bend', 5)
    return [(a[0] + h[0]) / 2 + face * b * (1 if i < nf else -1), (a[1] + h[1]) / 2]

for k in keys:  # make knees explicit so they interpolate
    p = P[str(k)]; kn = p.get('knees', {})
    p['knees'] = {str(i): kn.get(str(i), knee_default(p, i)) for i in range(len(p['hooves']))}

CAM = json.load(open('camera.json'))
raw_res = []
for f in range(N):
    k0 = max([k for k in keys if k <= f]); k1 = min([k for k in keys if k >= f])
    t = 0 if k1 == k0 else (f - k0) / (k1 - k0); te = ease(t)
    r = np.zeros(2)
    if cents[f] is not None and cents[k0] is not None and cents[k1] is not None:
        r = np.clip(cents[f] - (cents[k0] + (cents[k1] - cents[k0]) * te), -12, 12)
    raw_res.append(r)
raw_res = np.array(raw_res); RES = np.array([raw_res[max(0, f - 2):f + 3].mean(0) for f in range(N)])
for k in keys: RES[k] = 0
def lerp2(a, b, t): return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
def top_key(p, i):
    if i < 2: return lerp2(p['chest'], p['belly_f'], 0.25 + 0.5 * i)
    return lerp2(p['belly_h'], p.get('thigh', p['rump']), 0.25 + 0.5 * (i - 2))
LEN = []
for i in range(4):
    l1 = np.median([math.dist(top_key(P[str(k)], i), P[str(k)]['knees'][str(i)]) for k in keys])
    l2 = np.median([math.dist(P[str(k)]['knees'][str(i)], P[str(k)]['hooves'][i]) for k in keys])
    LEN.append((float(l1), float(l2)))
KL = {}
for k in keys:
    p = P[str(k)]; KL[k] = []
    for i in range(4):
        tp = top_key(p, i); kn_ = p['knees'][str(i)]; h = p['hooves'][i]
        cr = (h[0] - tp[0]) * (kn_[1] - tp[1]) - (h[1] - tp[1]) * (kn_[0] - tp[0])
        KL[k].append((math.dist(tp, kn_), math.dist(kn_, h), -1 if cr > 0 else 1))
frames = []; poses_out = []
for f in range(N):
    k0 = max([k for k in keys if k <= f]); k1 = min([k for k in keys if k >= f])
    t = 0 if k1 == k0 else (f - k0) / (k1 - k0); te = ease(t)
    A, B = P[str(k0)], P[str(k1)]
    pose = {}
    # mask residual: how far the mask centroid departs from the straight line between keyframe centroids
    res = RES[f]
    ki = keys.index(k0)
    Km1 = P[str(keys[max(0, ki - 1)])]; K2 = P[str(keys[min(len(keys) - 1, keys.index(k1) + 1)])]
    for n in BODY:
        p0, p1, p2, p3 = (np.array(Km1[n], float), np.array(A[n], float), np.array(B[n], float), np.array(K2[n], float))
        c = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
        pose[n] = [float(c[0] + res[0]), float(c[1] + res[1])]
    hv, kn = [], {}
    for i in range(4):
        cx0, cx1, cxf = CAM[k0][0], CAM[k1][0], CAM[f][0]
        a = [A['hooves'][i][0] - cx0, A['hooves'][i][1]]; b = [B['hooves'][i][0] - cx1, B['hooves'][i][1]]
        dx = b[0] - a[0]
        if abs(dx) < 12:      # planted: hold one world position for the whole interval
            wx = (a[0] + b[0]) / 2 if k0 != k1 else a[0]; wy = a[1] + (b[1] - a[1]) * te; lift = 0
            if f == k0: wx = a[0]
            elif f == k1: wx = b[0]
        else:
            lift = math.sin(math.pi * t) * min(10, abs(dx) * 0.35)
            wx = a[0] + dx * te; wy = a[1] + (b[1] - a[1]) * te - lift
        hv.append([wx + cxf, wy])
        ka, kb = A['knees'][str(i)], B['knees'][str(i)]
        kn[str(i)] = [ka[0] + (kb[0] - ka[0]) * te + res[0] * 0.5, ka[1] + (kb[1] - ka[1]) * te + res[1] * 0.5 - lift * 0.5]
    def top_of(i):
        if i < 2: return lerp2(pose['chest'], pose['belly_f'], 0.25 + 0.5 * i)
        return lerp2(pose['belly_h'], pose.get('thigh', pose['rump']), 0.25 + 0.5 * (i - 2))
    face = 1 if pose['nose'][0] >= pose['rump'][0] else -1
    for i in range(4):
        tp = top_of(i); h = hv[i]
        l1 = KL[k0][i][0] + (KL[k1][i][0] - KL[k0][i][0]) * te; l2 = KL[k0][i][1] + (KL[k1][i][1] - KL[k0][i][1]) * te
        side = KL[k0][i][2] if te < 0.5 else KL[k1][i][2]
        dx, dy = h[0] - tp[0], h[1] - tp[1]; d = math.hypot(dx, dy); d = min(d, (l1 + l2) * 0.999); d = max(d, abs(l1 - l2) + 1e-3)
        a = math.acos(max(-1, min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
        base = math.atan2(dy, dx); sgn = side   # bend to the same side the keyed knee was drawn on
        ang = base + sgn * a
        kn[str(i)] = [tp[0] + l1 * math.cos(ang), tp[1] + l1 * math.sin(ang)]
        hd = math.hypot(h[0] - tp[0], h[1] - tp[1])
        if hd > l1 + l2:  # unreachable: pull the hoof onto the reachable circle
            hv[i] = [tp[0] + dx / hd * (l1 + l2), tp[1] + dy / hd * (l1 + l2)]
    pose['hooves'] = hv; pose['knees'] = kn
    poses_out.append(pose)
    frames.append({'key': f in keys, 'strokes': [[[round(x, 1), round(y, 1)] for x, y in s] for s in draw(pose, prm)]})

json.dump(frames, open(sys.argv[3], 'w'), separators=(',', ':'))
json.dump(poses_out, open(sys.argv[3].replace('.json', '_poses.json'), 'w'))
# contact sheet
S = 2; cols = 11; tw, th = W // S, H // S
sheet = Image.new('RGB', (cols * tw, math.ceil(N / cols) * th), 'white'); d = ImageDraw.Draw(sheet)
for i, fr in enumerate(frames):
    ox, oy = (i % cols) * tw, (i // cols) * th
    d.rectangle([ox, oy, ox + tw - 1, oy + th - 1], fill=(250, 249, 244), outline=(200, 0, 0) if fr['key'] else (220, 220, 220))
    for s in fr['strokes']: d.line([(ox + x / S, oy + y / S) for x, y in s], fill=(20, 20, 20), width=2)
    d.text((ox + 3, oy + 2), str(i), fill=(120, 120, 120))
sheet.save(sys.argv[3].replace('.json', '_sheet.png'))
print(N, 'frames')
