"""Style and fit terms of the keyframe reward.
style: how typical the drawing's stroke statistics are among 4,971 recognized Quick, Draw! giraffes
       (percentile of mean distance to 25 nearest neighbours; 100 = as typical as the most typical real doodle)
fit:   pose fidelity to the SAM mask: share of ink inside the mask (dilated 6px) x bbox agreement
"""
import os
QD = os.environ.get('QD_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'quickdraw'))
import json, math, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

def feats(strokes):
    pts = [p for s in strokes for p in s]
    xs = np.array([p[0] for p in pts], float); ys = np.array([p[1] for p in pts], float)
    sc = 255 / max(xs.max() - xs.min(), ys.max() - ys.min(), 1)
    segs = []; turns = []
    for s in strokes:
        a = np.array(s, float) * sc
        if len(a) > 1: segs += list(np.hypot(*np.diff(a, axis=0).T))
        if len(a) > 2:
            v = np.diff(a, axis=0); ang = np.arctan2(v[:, 1], v[:, 0]); d = np.abs(np.angle(np.exp(1j * np.diff(ang))))
            turns += list(d)
    segs = np.array(segs) if segs else np.array([0.0]); turns = np.array(turns) if turns else np.array([0.0])
    w = (xs.max() - xs.min()) * sc; h = (ys.max() - ys.min()) * sc
    return np.array([len(strokes), math.log(len(pts)), np.median(segs), segs.sum() / 255, np.mean(turns), w / max(h, 1)])

_ref = None
def ref():
    global _ref
    if _ref is None:
        rows = [json.loads(l) for l in open(f'{QD}/giraffe.part').read().splitlines()[:-1]]
        F = np.array([feats([list(zip(*s)) for s in r['drawing']]) for r in rows if r['recognized']])
        mu, sd = F.mean(0), F.std(0) + 1e-6; Z = (F - mu) / sd
        # typicality of each real drawing (leave-one-out kNN mean distance)
        D = np.sqrt(((Z[:1500, None, :] - Z[None, :, :]) ** 2).sum(-1)); D.sort(1)
        real_knn = D[:, 1:26].mean(1)
        _ref = (Z, mu, sd, np.sort(real_knn))
    return _ref

def style(strokes):
    Z, mu, sd, real_knn = ref()
    z = (feats(strokes) - mu) / sd
    d = np.sqrt(((Z - z) ** 2).sum(1)); d.sort(); k = d[:25].mean()
    return float(100 * (1 - np.searchsorted(real_knn, k) / len(real_knn)))

def fit(strokes, polys, W=480, H=360):
    m = Image.new('L', (W, H), 0); dm = ImageDraw.Draw(m)
    for p in polys: dm.polygon([tuple(q) for q in p], fill=255)
    M = ndimage.binary_dilation(np.array(m) > 0, iterations=6)
    ink = Image.new('L', (W, H), 0); di = ImageDraw.Draw(ink)
    for s in strokes: di.line([tuple(q) for q in s], fill=255, width=2)
    I = np.array(ink) > 0
    inside = (I & M).sum() / max(I.sum(), 1)
    def bb(a):
        ys, xs = np.nonzero(a); return xs.min(), ys.min(), xs.max(), ys.max()
    a = bb(np.array(m) > 0); b = bb(I)
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy; uni = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return float(inside * inter / max(uni, 1))
