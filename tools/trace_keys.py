"""Trace held raster keys into Quick, Draw!-style strokes.

This is the bridge between the two lanes:
  look lane  - an image model draws a strong still key in the doodle's identity (raster, no motion)
  motion lane - vector strokes that can be in-betweened, layered on planes and measured
A traced key keeps the look and becomes editable, measurable vector data.

usage: python3 tools/trace_keys.py <batch_dir> <out_json>
reads  <batch_dir>/subjects/<name>/art-key-<i>.png
writes one JSON: {subject: {keys: [{strokes, n_strokes, points, recall, precision}], W, H}}
strokes are [[x0,y0],[x1,y1],...] in key-image pixels.
recall    = share of original ink within (line half-width + 2) px of a traced line (did we keep the drawing?)
parts_kept = share of ink pieces (>=20 px) that some traced line touches (did we drop an eye?)
precision = share of traced ink within 2 px of original ink (did we invent lines?)
"""
import json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from skimage.morphology import skeletonize
from scipy import ndimage

NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def rdp(pts, eps):
    if len(pts) < 3: return pts
    if math.dist(pts[0], pts[-1]) < 1e-6:          # closed path: split at the farthest point first
        i = max(range(len(pts)), key=lambda k: math.dist(pts[0], pts[k]))
        if i == 0: return pts[:1]
        return rdp(pts[:i + 1], eps)[:-1] + rdp(pts[i:], eps)
    a, b = np.array(pts[0], float), np.array(pts[-1], float); ab = b - a; L = np.hypot(*ab) or 1e-9
    d = [abs(ab[0] * (p[1] - a[1]) - ab[1] * (p[0] - a[0])) / L for p in pts[1:-1]]
    i = int(np.argmax(d)) + 1
    if d[i - 1] > eps: return rdp(pts[:i + 1], eps)[:-1] + rdp(pts[i:], eps)
    return [pts[0], pts[-1]]


def trace(img, ink_thresh=170, min_len=2, eps=1.1):
    g = np.asarray(img.convert('L'), float)
    ink = g < ink_thresh
    ink = ndimage.binary_closing(ink, iterations=1)
    sk = skeletonize(ink)
    H, W = sk.shape
    deg = ndimage.convolve(sk.astype(int), np.ones((3, 3), int), mode='constant') - 1
    deg[~sk] = 0
    node = sk & (deg != 2)                       # endpoints and junctions
    used = np.zeros_like(sk); paths = []; node_edges = set()
    def nbrs(y, x):
        for dy, dx in NB:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W and sk[yy, xx]: yield yy, xx
    def walk(start, nxt):
        path = [start, nxt]; cur = nxt
        while not node[cur]:
            used[cur] = True
            step = [q for q in nbrs(*cur) if not used[q] and q != path[-2] and (node[q] or True)]
            step = sorted(step, key=lambda q: (not node[q] and False, abs(q[0] - cur[0]) + abs(q[1] - cur[1])))
            if not step: break
            cur = step[0]; path.append(cur)
        return path
    for y, x in zip(*np.nonzero(node)):
        if deg[y, x] == 0:                       # a filled dot (an eye) skeletonizes to one pixel
            paths.append([(y, x), (y, x + 1)]); continue
        for n in list(nbrs(y, x)):
            if node[n]:
                e = tuple(sorted([(y, x), n]))
                if e not in node_edges: node_edges.add(e); paths.append([(y, x), n])
            elif not used[n]:
                paths.append(walk((y, x), n))
    # closed loops with no node (an eye, a bowl rim)
    for y, x in zip(*np.nonzero(sk & ~node & ~used)):
        if used[y, x]: continue
        start = (y, x); used[start] = True; p = [start]; cur = start
        while True:
            step = [q for q in nbrs(*cur) if not used[q]]
            if not step: break
            cur = step[0]; used[cur] = True; p.append(cur)
        if math.dist(p[-1], start) <= 1.5 and len(p) > 2: p.append(start)
        paths.append(p)
    comp, nc = ndimage.label(sk, structure=np.ones((3, 3)))
    comp_size = np.bincount(comp.ravel())
    strokes = []
    for p in paths:
        L = sum(math.dist(a, b) for a, b in zip(p[:-1], p[1:]))
        if L < min_len and comp_size[comp[p[0]]] > 6: continue   # drop short spurs, keep whole tiny dots
        s = rdp([[float(x), float(y)] for y, x in p], eps)
        strokes.append(s)
    strokes = join(strokes)
    hw = float(np.median(ndimage.distance_transform_edt(ink)[sk])) if sk.any() else 1.0
    return strokes, ink, hw


def join(strokes, tol=2.5):
    """Greedy end-to-end merging so a contour broken at a junction reads as one pen stroke."""
    out = [s[:] for s in strokes]; merged = True
    while merged:
        merged = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                a, b = out[i], out[j]
                for ra in (False, True):
                    for rb in (False, True):
                        A = a[::-1] if ra else a; B = b[::-1] if rb else b
                        if math.dist(A[-1], B[0]) <= tol and turn(A, B) < 0.6:
                            out[i] = A + B[1:]; out.pop(j); merged = True; break
                    if merged: break
                if merged: break
            if merged: break
    return out


def turn(A, B):
    if len(A) < 2 or len(B) < 2: return 0
    u = np.subtract(A[-1], A[-2]); v = np.subtract(B[1], B[0])
    c = np.dot(u, v) / ((np.hypot(*u) * np.hypot(*v)) or 1)
    return 1 - c


def score(strokes, ink, W, H, hw=1.0):
    m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
    for s in strokes: d.line([tuple(p) for p in s], fill=255, width=1)
    traced = np.asarray(m) > 0
    near_t = ndimage.binary_dilation(traced, iterations=int(math.ceil(hw)) + 2)
    near_i = ndimage.binary_dilation(ink, iterations=2)
    recall = float((ink & near_t).sum() / max(1, ink.sum()))
    precision = float((traced & near_i).sum() / max(1, traced.sum()))
    lab, n = ndimage.label(ink, structure=np.ones((3, 3)))
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    big = [i + 1 for i in range(n) if sizes[i] >= 20]
    hit = set(np.unique(lab[traced & ink])) if big else set()
    parts = float(sum(1 for i in big if i in hit) / max(1, len(big)))
    return recall, precision, parts


def split_layers(entry, tol=3, share=0.9):
    """A stroke that sits on ink in every other key of the shot is set dressing: it goes on the
    background plane. Strokes that change between keys are the performance: the character plane."""
    W, H = entry['W'], entry['H']; near = []
    for k in entry['keys']:
        m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
        for s in k['strokes']: d.line([tuple(p) for p in s], fill=255, width=1)
        near.append(ndimage.binary_dilation(np.asarray(m) > 0, iterations=tol))
    for i, k in enumerate(entry['keys']):
        layer = []
        for s in k['strokes']:
            pts = dense(s)
            ok = all(np.mean([near[j][min(H - 1, max(0, int(round(y)))), min(W - 1, max(0, int(round(x))))] for x, y in pts]) >= share
                     for j in range(len(entry['keys'])) if j != i)
            layer.append('bg' if ok else 'char')
        k['layer'] = layer
        k['char_strokes'] = layer.count('char')


def dense(s, step=2.0):
    out = [s[0]]
    for a, b in zip(s[:-1], s[1:]):
        n = max(1, int(math.dist(a, b) // step))
        out += [[a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n] for t in range(1, n + 1)]
    return out


def main(batch, out):
    res = {}
    for sd in sorted(Path(batch, 'subjects').iterdir()):
        keys = sorted(sd.glob('art-key-*.png'))
        if not keys: continue
        entry = {'keys': []}
        for k in keys:
            im = Image.open(k); W, H = im.size
            st, ink, hw = trace(im)
            r, p, parts = score(st, ink, W, H, hw)
            entry['W'], entry['H'] = W, H
            entry['keys'].append({'file': f'subjects/{sd.name}/{k.name}', 'n_strokes': len(st), 'points': sum(len(s) for s in st),
                                  'recall': round(r, 3), 'precision': round(p, 3), 'parts_kept': round(parts, 3), 'half_width': round(hw, 2),
                                  'strokes': [[[round(x, 1), round(y, 1)] for x, y in s] for s in st]})
        split_layers(entry)
        res[sd.name] = entry
        ks = entry['keys']
        print(f"{sd.name:11s} strokes {np.mean([k['n_strokes'] for k in ks]):6.1f}  recall {np.mean([k['recall'] for k in ks]):.3f}  precision {np.mean([k['precision'] for k in ks]):.3f}  parts {min(k['parts_kept'] for k in ks):.3f} (worst key)  char/total {np.mean([k['char_strokes'] for k in ks]):.0f}/{np.mean([k['n_strokes'] for k in ks]):.0f}")
    json.dump(res, open(out, 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
