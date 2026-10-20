"""The Giraffe Walks Past method, with the drawn keys we already have.

The batch holds four keys per subject, drawn by an image model in the chosen doodle's identity and each
approved by a fresh critic as matching the footage pose. This puts those drawings over SAM silhouettes:

1. align   each drawing is carried from its still onto the excerpt frame the still matches (tools/key_align.py);
           the drawing is not moved or resized: it was drawn over the footage and is already in place
           (an earlier version searched a scale and shift against the SAM mask; that pulled the character
           away from the scenery it was drawn with and showed the subject twice)
2. split   point by point: within 25 px of this frame's silhouette a line is character, unless at least two
           other keys drew it too away from their own subject (a door jamb in front of the rabbit); farther out
           it is scenery. Long straight lines running off the silhouette are scenery.
3. plate   the scenery is drawn once: key 0's scenery plus what later keys add
4. tween   character strokes are matched key to key and interpolated; every frame is then pulled onto that
           frame's silhouette (centre and size), as Giraffe Walks Past added the SAM residual to its in-betweens
5. cel     the silhouette is painted under the character so scenery does not show through it

usage: python3 tools/sam_keys.py <category> [...]   (after tools/sam_import.py and tools/key_align.py)
writes shots/<cat>-sam/shot.json (projector and shot-page schema), keys.png, strip.png
"""
import json, math, sys
from pathlib import Path
import numpy as np, cv2

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / 'batches/2026-10-20-selected-drawings'
sys.path.insert(0, str(ROOT / 'tools'))
from match_strokes import resample, match
sys.path.insert(0, str(ROOT / 'tools'))


def raster(polys, W, H):
    m = np.zeros((H, W), np.uint8)
    for p in polys:
        if len(p) >= 3: cv2.fillPoly(m, [np.array(p, np.int32)], 1)
    return m > 0


def dense(s, step=2.0):
    a = np.array(s, float)
    if len(a) == 1: return a
    out = [a[0]]
    for p, q in zip(a[:-1], a[1:]):
        k = max(1, int(np.hypot(*(q - p)) // step)); out += [p + (q - p) * t / k for t in range(1, k + 1)]
    return np.array(out)


def inside_frac(s, m):
    d = dense(s); H, W = m.shape
    x = np.clip(np.round(d[:, 0]).astype(int), 0, W - 1); y = np.clip(np.round(d[:, 1]).astype(int), 0, H - 1)
    ok = (d[:, 0] >= 0) & (d[:, 0] < W) & (d[:, 1] >= 0) & (d[:, 1] < H)
    return float((m[y, x] & ok).mean())


def straight_and_long(s, mask):
    """Door frames, fence rails and horizons cross the subject but are scenery: long, nearly straight lines."""
    a = np.array(s, float)
    if len(a) < 2: return False
    L = np.hypot(*np.diff(a, axis=0).T).sum(); chord = np.hypot(*(a[-1] - a[0]))
    ys, xs = np.nonzero(mask); size = max(np.ptp(xs), np.ptp(ys)) if len(xs) else 1
    return L > 0.45 * size and chord / max(L, 1e-9) > 0.93


def split(strokes, mask, grow, share=0.6):
    m = cv2.dilate(mask.astype(np.uint8), np.ones((2 * grow + 1, 2 * grow + 1), np.uint8)) > 0
    ch, bg = [], []
    for s in strokes: (ch if inside_frac(s, m) >= share and not straight_and_long(s, mask) else bg).append(s)
    return ch, bg


def clip_to(strokes, mask, grow):
    """Cut character strokes where they leave the (dilated) silhouette: a traced line that ran on into a
    door frame or the ground keeps only its part on the subject."""
    m = cv2.dilate(mask.astype(np.uint8), np.ones((2 * grow + 1, 2 * grow + 1), np.uint8)) > 0; H, W = m.shape
    out = []
    for s in strokes:
        d = dense(s, 1.5); x = np.clip(np.round(d[:, 0]).astype(int), 0, W - 1); y = np.clip(np.round(d[:, 1]).astype(int), 0, H - 1)
        ins = m[y, x]; run = []
        for p, ok in zip(d, ins):
            if ok: run.append(p.tolist())
            elif run: out.append(run); run = []
        if run: out.append(run)
    from trace_keys import rdp
    return [rdp(r, 0.8) for r in out if len(r) > 1]


def fit_score(strokes, mask):
    if not strokes: return 0.0
    m = cv2.dilate(mask.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    pts = np.concatenate([dense(s) for s in strokes]); H, W = mask.shape
    x = np.clip(np.round(pts[:, 0]).astype(int), 0, W - 1); y = np.clip(np.round(pts[:, 1]).astype(int), 0, H - 1)
    inside = m[y, x].mean()
    ys, xs = np.nonzero(mask)
    if not len(xs): return 0.0
    a = (xs.min(), ys.min(), xs.max(), ys.max()); b = (*pts.min(0), *pts.max(0))
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy; uni = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return float(inside * inter / max(uni, 1))


def register(strokes, mask):
    """Scale about the drawing's centre and shift, to best fit the silhouette. Returns transformed strokes, params, before/after fit."""
    pts = np.concatenate([np.array(s, float) for s in strokes]); c = pts.mean(0)
    T = lambda s, k, dx, dy: [((np.array(q, float) - c) * k + c + [dx, dy]).tolist() for q in s]
    apply = lambda k, dx, dy: [T(s, k, dx, dy) for s in strokes]
    base = fit_score(strokes, mask); best = (base, 1.0, 0.0, 0.0)
    for k in (0.75, 0.85, 0.95, 1.0, 1.08, 1.18, 1.3):
        for dx in range(-40, 41, 8):
            for dy in range(-40, 41, 8):
                sc = fit_score(apply(k, dx, dy), mask)
                if sc > best[0]: best = (sc, k, dx, dy)
    _, k, dx, dy = best
    for step in (4, 2, 1):
        for kk in (k * 0.97, k, k * 1.03):
            for ddx in (dx - step, dx, dx + step):
                for ddy in (dy - step, dy, dy + step):
                    sc = fit_score(apply(kk, ddx, ddy), mask)
                    if sc > best[0]: best = (sc, kk, ddx, ddy)
        _, k, dx, dy = best
    if best[0] < base + 0.03: return strokes, {'scale': 1.0, 'dx': 0, 'dy': 0}, base, base   # not worth moving
    return apply(k, dx, dy), {'scale': round(k, 3), 'dx': round(dx, 1), 'dy': round(dy, 1)}, base, best[0]


def run(cat):
    d = ROOT / 'shots' / f'{cat}-sam'
    clip = json.load(open(d / 'clip.json')); n, W, H, keys = clip['n'], clip['W'], clip['H'], clip['keys']
    M = json.load(open(d / 'masks.json')); masks = [raster(M[str(f)], W, H) for f in range(n)]
    cam = json.load(open(d / 'camera.json'))
    T = json.load(open(ROOT / 'traced/traced_keys.json'))[cat]['keys']
    src = json.load(open(B / 'subjects' / cat / 'source.json'))['source']
    review = json.load(open(B / json.load(open(B / 'subjects' / cat / 'preview-data.json'))['review_path']))
    # Each drawing stays where it was drawn. key_align.json gives the excerpt frame its still matches and the
    # (near-identity) transform from still to that frame; nothing is rescaled or moved to chase a mask.
    AL = json.load(open(d / 'key_align.json'))
    keys = [a['frame'] for a in AL]
    Ms = [np.array(a['M'], float) for a in AL]
    drawn = []
    for i, k in enumerate(keys):
        st = [s for s in T[i]['strokes'] if len(s) >= 2]
        drawn.append([(np.c_[np.array(s, float), np.ones(len(s))] @ Ms[i].T) for s in st])
    # world coordinates of key 0 (camera removed), to compare drawings across keys
    off = [np.array(cam[keys[0]], float) - np.array(cam[k], float) for k in keys]
    def ras(strokes, o, r):
        m = np.zeros((H, W), np.uint8)
        for q in strokes: cv2.polylines(m, [np.round(q + o).astype(np.int32)], False, 1, 1)
        return cv2.dilate(m, np.ones((2 * r + 1, 2 * r + 1), np.uint8)) > 0
    inkw = [ras(drawn[i], off[i], 4) for i in range(len(keys))]
    maskw = [np.roll(np.roll(masks[k], int(round(off[i][1])), 0), int(round(off[i][0])), 1) for i, k in enumerate(keys)]
    grow = lambda m, r: cv2.dilate(m.astype(np.uint8), np.ones((2 * r + 1, 2 * r + 1), np.uint8)) > 0
    near6 = [grow(masks[k], 6) for k in keys]; near25 = [grow(masks[k], 25) for k in keys]
    maskw25 = [grow(m, 25) for m in maskw]
    def at(m, x, y): return bool(m[min(max(int(round(y)), 0), H - 1), min(max(int(round(x)), 0), W - 1)])
    char, bgs, reg = [], [], []
    for i, k in enumerate(keys):
        ch, bg = [], []
        for q in drawn[i]:
            pts = dense(q.tolist(), 2.0); lab = []
            for x, y in pts:
                wx, wy = x + off[i][0], y + off[i][1]
                others = [j for j in range(len(keys)) if j != i]
                # scenery: other keys drew it too, away from their own subject
                seen_clear = sum(at(inkw[j], wx, wy) and not at(maskw25[j], wx, wy) for j in others)
                if at(near25[i], x, y): lab.append('bg' if seen_clear >= 2 else 'char')
                else: lab.append('bg')
            # runs of one label; drop tiny runs by giving them their neighbours' label
            runs = []
            for p_, l in zip(pts, lab):
                if runs and runs[-1][0] == l: runs[-1][1].append(p_)
                else: runs.append([l, [p_]])
            for r in range(len(runs)):
                if len(runs[r][1]) < 4 and len(runs) > 1:
                    nb = runs[r - 1][0] if r > 0 else runs[r + 1][0]; runs[r][0] = nb
            merged = []
            for l, ps in runs:
                if merged and merged[-1][0] == l: merged[-1][1].extend(ps)
                else: merged.append([l, list(ps)])
            for l, ps in merged:
                ps = np.array(ps)[::2] if len(ps) > 6 else np.array(ps)
                if len(ps) < 2: continue
                (ch if l == 'char' else bg).append(ps.tolist())
        # door jambs, rails and floor lines: long, straight, and running off the silhouette
        ch2 = []
        for q in ch:
            if straight_and_long(q, masks[k]) and inside_frac(q, near6[i]) < 0.7: bg.append(q)
            else: ch2.append(q)
        ch = [q for q in ch2 if np.hypot(*np.diff(np.array(q), axis=0).T).sum() >= 6]
        char.append(ch); bgs.append(bg)
        reg.append({'frame': k, 'still_to_frame_scale': AL[i]['scale'], 'still_to_frame_shift': AL[i]['shift'], 'moved': False,
                    'fit': round(fit_score(ch, masks[k]), 3), 'char_strokes': len(ch), 'scenery_strokes': len(bg)})
    # plate: key 0's scenery, drawn once; later keys add only what key 0's subject covered and their own subject does not
    hole = grow(masks[keys[0]], 5)
    plate = [q for q in bgs[0]]
    for i in range(1, len(keys)):
        for q in bgs[i]:
            q0 = np.array(q) + off[i]
            if inside_frac(q0.tolist(), hole) > 0.7 and inside_frac(q, grow(masks[keys[i]], 4)) < 0.2: plate.append(q0.tolist())
    plate = [q for q in plate if len(q) > 1 and np.hypot(*np.diff(np.array(q), axis=0).T).sum() >= 8]
    # in-betweens
    R = [[resample(s) for s in ch] for ch in char]
    stats = [(np.concatenate(R[i]).mean(0) if R[i] else np.zeros(2)) for i in range(len(keys))]
    area = lambda m: math.sqrt(max(m.sum(), 1))
    mc = [np.argwhere(m)[:, ::-1].mean(0) if m.any() else None for m in masks]
    ma = [area(m) if m.any() else None for m in masks]
    # smooth silhouette centre and size over 5 frames, like the giraffe's residual
    def smooth(v):
        out = []
        for f in range(n):
            w = [v[j] for j in range(max(0, f - 2), min(n, f + 3)) if v[j] is not None]
            out.append(np.mean(w, 0) if w else None)
        return out
    mcs, mas = smooth(mc), smooth(ma)
    pairs = []
    for a in range(len(keys) - 1):
        m, LA, LB, t = match(R[a], R[a + 1], W, H); pairs.append(m)
    share = []
    for a, m in enumerate(pairs):
        LA = [float(np.hypot(*np.diff(r, axis=0).T).sum()) for r in R[a]]; LB = [float(np.hypot(*np.diff(r, axis=0).T).sum()) for r in R[a + 1]]
        share.append(round((sum(LA[i] for i, _, _ in m) + sum(LB[j] for _, j, _ in m)) / max(sum(LA) + sum(LB), 1), 3))
    cast = []
    for f in range(n):
        if f <= keys[0]: fr = [np.array(s, float) for s in char[0]]; a, t = 0, 0.0
        elif f >= keys[-1]: fr = [np.array(s, float) for s in char[-1]]; a, t = len(keys) - 1, 0.0
        else:
            a = max(i for i, k in enumerate(keys) if k <= f); t = (f - keys[a]) / (keys[a + 1] - keys[a]); te = t * t * (3 - 2 * t)
            A, Bk, m = R[a], R[a + 1], pairs[a]; ma_, mb_ = {i for i, _, _ in m}, {j for _, j, _ in m}
            fr = [A[i] + ((Bk[j][::-1] if r else Bk[j]) - A[i]) * te for i, j, r in m]
            fr += [np.array(char[a][i], float) for i in range(len(A)) if i not in ma_] if t < 0.5 else [np.array(char[a + 1][j], float) for j in range(len(Bk)) if j not in mb_]
            # pull onto this frame's silhouette
            ka, kb = keys[a], keys[a + 1]
            if all(x is not None for x in (mcs[f], mcs[ka], mcs[kb], mas[f], mas[ka], mas[kb])):
                c_t = mcs[ka] + (mcs[kb] - mcs[ka]) * te; s_t = mas[ka] + (mas[kb] - mas[ka]) * te
                k_ = float(np.clip(mas[f] / s_t, 0.85, 1.18)); off = np.clip(mcs[f] - c_t, -25, 25)
                fr = [c_t + off + (s - c_t) * k_ for s in fr]
        cast.append([np.round(s, 1).tolist() for s in fr if len(s)])
    notes = {k: e.get('evidence', '')[:120] for k, e in zip(keys, review.get('timed_key_evidence', [{}] * len(keys)))}
    shot = {'title': f'{cat.capitalize()}, Drawn Keys over SAM', 'category': cat, 'fps': 12, 'W': W, 'H': H, 'z_ref': 3,
            'source': {'film': src.get('source_title') or 'Moving Image Archive', 'url': src.get('shot_page_url')},
            'planes': [{'id': 'set', 'z': 3, 'label': 'Scenery, drawn once'}, {'id': 'char', 'z': 2, 'label': cat.capitalize()}],
            'camera': cam,
            'objects': [{'id': 'scenery', 'plane': 'set', 'z': 3, 'class': 'ground', 'source': 'look-lane keys traced; character removed with SAM; key 0 plus what the subject hid',
                         'strokes': [np.round(np.array(s, float), 1).tolist() for s in plate]}],
            'cast': {'frames': cast, 'keys': keys, 'look_keys': keys, 'source': 'the four approved look-lane keys, traced, left where they were drawn; character and scenery split point by point'},
            'xsheet': [{'f': f, 'drawing': f'K{keys.index(f) + 1:02d}' if f in keys else f'B{f:02d}', 'kind': 'K' if f in keys else 'B',
                        'cam': [round(cam[f][0], 1), round(cam[f][1], 1)], 'note': notes.get(f, '')} for f in range(n)],
            'footage': [f'frames/f{f:03d}.jpg' for f in range(n)], 'masks': [M[str(f)] for f in range(n)],
            'registration': reg, 'matched_ink': share, 'plate_strokes': len(plate)}
    (d / 'shot.json').write_text(json.dumps(shot, separators=(',', ':')))
    sheets(d, shot, masks)
    print(cat, 'keys', keys, 'char', [r['char_strokes'] for r in reg], 'fit', [r['fit'] for r in reg], 'matched', share, 'plate', len(plate))


def sheets(d, S, masks):
    from PIL import Image, ImageDraw
    W, H, keys, cam = S['W'], S['H'], S['cast']['keys'], S['camera']
    def frame(f, footage):
        if footage:
            im = Image.open(d / 'frames' / f'f{f:03d}.jpg').convert('RGB'); im = Image.blend(im, Image.new('RGB', im.size, 'white'), 0.5)
        else: im = Image.new('RGB', (W, H), 'white')
        g = ImageDraw.Draw(im)
        for s in S['objects'][0]['strokes']:
            g.line([(x + cam[f][0], y + cam[f][1]) for x, y in s], fill=(150, 145, 138), width=1)
        if not footage:
            m = Image.fromarray((masks[f] * 255).astype(np.uint8)); im.paste((255, 255, 255), mask=m)
        for p in S['masks'][f]:
            if footage and len(p) > 2: g.line([tuple(q) for q in p] + [tuple(p[0])], fill=(40, 120, 230), width=1)
        for s in S['cast']['frames'][f]:
            if len(s) > 1: g.line([tuple(q) for q in s], fill=(200, 60, 0) if footage else (22, 20, 18), width=2)
        return im
    sh = Image.new('RGB', (2 * W + 4, 2 * H + 4), 'white')
    for i, k in enumerate(keys[:4]): sh.paste(frame(k, True), ((i % 2) * (W + 4), (i // 2) * (H + 4)))
    sh.save(d / 'keys.png')
    n = len(S['cast']['frames']); fr = [round(i * (n - 1) / 11) for i in range(12)]; tw, th = W // 2, H // 2
    st = Image.new('RGB', (4 * tw, 3 * th), 'white')
    for i, f in enumerate(fr): st.paste(frame(f, False).resize((tw, th)), ((i % 4) * tw, (i // 4) * th))
    st.save(d / 'strip.png')


if __name__ == '__main__':
    for c in sys.argv[1:]: run(c)
