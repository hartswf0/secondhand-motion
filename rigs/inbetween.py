"""Keys -> every frame, as Giraffe Walks Past step 7: Catmull-Rom through the keys for every pose point,
plus the SAM residual (how far the silhouette centre departs from the line between the keys' silhouette
centres, smoothed over 5 frames, clipped), so in-betweens follow the real animal and not only the keys.
usage: python3 rigs/inbetween.py <shot_dir> <rig.py> <poses.json>  -> <shot_dir>/drawn_frames.json"""
import json, sys, importlib.util
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from sam_keys import raster


def load_rig(path):
    spec = importlib.util.spec_from_file_location('rig', path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def run(d, rigp, posep, clip_res=14):
    d = Path(d); rig = load_rig(rigp); P = {int(k): v for k, v in json.load(open(posep)).items()}
    clip = json.load(open(d / 'clip.json')); n, W, H = clip['n'], clip['W'], clip['H']
    prm = json.load(open(d / 'rig_params.json')) if (d / 'rig_params.json').exists() else {}
    M = json.load(open(d / 'masks.json'))
    cents = []
    for f in range(n):
        m = raster(M[str(f)], W, H); ys, xs = np.nonzero(m)
        cents.append(np.array([xs.mean(), ys.mean()]) if len(xs) else None)
    areas = []
    for f in range(n):
        m = raster(M[str(f)], W, H); areas.append(float(np.sqrt(m.sum())) if m.any() else np.nan)
    areas = np.array(areas)
    keys = sorted(P); names = [k for k in P[keys[0]] if isinstance(P[keys[0]][k], list) and not isinstance(P[keys[0]][k][0], list)]
    raw = []
    for f in range(n):
        k0 = max([k for k in keys if k <= f], default=keys[0]); k1 = min([k for k in keys if k >= f], default=keys[-1])
        t = 0 if k1 == k0 else (f - k0) / (k1 - k0); te = t * t * (3 - 2 * t); r = np.zeros(2)
        if all(c is not None for c in (cents[f], cents[k0], cents[k1])):
            r = np.clip(cents[f] - (cents[k0] + (cents[k1] - cents[k0]) * te), -clip_res, clip_res)
        raw.append(r)
    raw = np.array(raw); RES = np.array([raw[max(0, f - 2):f + 3].mean(0) for f in range(n)])
    for k in keys: RES[k] = 0
    # drawing size from the silhouette: doodle units -> px = k * sqrt(mask area), k calibrated on the keys
    # whose root points are spread (profile keys), so a turned or stretched body does not resize the doodle
    sp = getattr(getattr(rig, '_R', None), 'sp', None); scale_k = None
    if sp and sp.get('size_from_mask', True) and 'root' in sp:
        a0, a1 = sp['root']; t = np.hypot(*(np.array(sp['anchors'][a1], float) - np.array(sp['anchors'][a0], float)))
        rat = [np.hypot(*(np.array(P[k][a1], float) - np.array(P[k][a0], float))) / t / areas[k] for k in keys if not np.isnan(areas[k])]
        scale_k = float(np.percentile(rat, 60)) * sp.get('scale_mult', 1.0) if rat else None
    sm = np.where(np.isnan(areas), np.nanmedian(areas), areas)
    sm_area = np.array([sm[max(0, f - 2):f + 3].mean() for f in range(n)])
    if sp and sp.get('size') == 'steady':   # one size for the whole shot: the doodle does not grow or shrink
        sm_area = np.full(n, float(np.nanmedian(sm_area)))
    if sp and sp.get('area_cap'): sm_area = np.minimum(sm_area, np.nanpercentile(sm_area, sp['area_cap']))
    # Optical-flow tracking of every pose point between keys (the footage moves the drawing on every frame, as
    # the giraffe's SAM residual did for its body centre, here point by point). Each point is tracked forward
    # from the key before and backward from the key after (pyramidal Lucas-Kanade on the footage); the two
    # tracks are blended by position between the keys and then corrected so they land exactly on both keys.
    # A track that fails (lost, or straying more than 40 px from the plain interpolation) falls back to it.
    track = (sp or {}).get('track', True)
    import cv2
    G = [cv2.cvtColor(cv2.imread(str(d / 'frames' / f'f{f:03d}.jpg')), cv2.COLOR_BGR2GRAY) for f in range(n)] if track else None
    lk = dict(winSize=(21, 21), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    def follow(pts, a, b):
        out = {a: pts.copy()}; cur = pts.astype(np.float32).reshape(-1, 1, 2); ok = np.ones(len(pts), bool); step = 1 if b > a else -1
        for f in range(a, b, step):
            nxt, st, err = cv2.calcOpticalFlowPyrLK(G[f], G[f + step], cur, None, **lk)
            ok &= st.ravel() == 1; cur = np.where(ok[:, None, None], nxt, cur); out[f + step] = cur.reshape(-1, 2).copy()
        return out, ok
    flow = {}
    if track:
        for i in range(len(keys) - 1):
            a, b = keys[i], keys[i + 1]
            if b - a < 2: continue
            A = np.array([P[a][nm] for nm in names], float); B = np.array([P[b][nm] for nm in names], float)
            fw, okf = follow(A, a, b); bw, okb = follow(B, b, a)
            for f in range(a + 1, b):
                t = (f - a) / (b - a)
                # residual of each track at the far key, spread linearly so the blend meets both keys
                tf = fw[f] + (B - fw[b]) * t; tb = bw[f] + (A - bw[a]) * (1 - t)
                flow[f] = (tf * (1 - t) + tb * t, okf & okb)
    poses, frames = [], []
    for f in range(n):
        k0 = max([k for k in keys if k <= f], default=keys[0]); k1 = min([k for k in keys if k >= f], default=keys[-1])
        t = 0 if k1 == k0 else (f - k0) / (k1 - k0)
        i0 = keys.index(k0); i1 = keys.index(k1)
        A, B = P[k0], P[k1]; Am, Bp = P[keys[max(0, i0 - 1)]], P[keys[min(len(keys) - 1, i1 + 1)]]
        pose = {}
        for nm in names:
            p0, p1, p2, p3 = (np.array(X[nm], float) for X in (Am, A, B, Bp))
            c = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
            pose[nm] = [float(c[0] + RES[f][0]), float(c[1] + RES[f][1])]
            if f in flow:
                j = names.index(nm); q, okq = flow[f]
                if okq[j] and np.hypot(*(q[j] - c)) < 40: pose[nm] = [float(q[j][0]), float(q[j][1])]
        if scale_k is not None and not np.isnan(sm_area[f]): pose['_scale'] = float(scale_k * sm_area[f])
        for nm, v in A.items():   # number-valued pose entries (a wing's open amount) ease between the keys
            if isinstance(v, (int, float)) and nm in B:
                pose[nm] = float(v + (B[nm] - v) * (t * t * (3 - 2 * t)))
        poses.append(pose)
    # light temporal smoothing of every point (3-frame weights 1-2-1), keys held exactly
    if track:
        sm = []
        for f in range(n):
            if f in keys or f == 0 or f == n - 1: sm.append(poses[f]); continue
            q = dict(poses[f])
            for nm in names: q[nm] = [float((poses[f - 1][nm][k] + 2 * poses[f][nm][k] + poses[f + 1][nm][k]) / 4) for k in (0, 1)]
            sm.append(q)
        poses = sm
    sig = (sp or {}).get('smooth', 0)
    if sig:   # Gaussian smoothing of every pose value over time (keys included): removes steps at keys and size jumps
        rad = int(3 * sig); w = np.exp(-0.5 * (np.arange(-rad, rad + 1) / sig) ** 2)
        def sm1(vals):
            v = np.array(vals, float); pad = np.concatenate([np.repeat(v[:1], rad, 0), v, np.repeat(v[-1:], rad, 0)])
            return [float(np.dot(w, pad[i:i + 2 * rad + 1]) / w.sum()) for i in range(len(v))]
        keysets = set().union(*[set(q) for q in poses])
        for nm in keysets:
            if all(nm in q for q in poses):
                if isinstance(poses[0][nm], list):
                    xs = sm1([q[nm][0] for q in poses]); ys = sm1([q[nm][1] for q in poses])
                    for i, q in enumerate(poses): q[nm] = [xs[i], ys[i]]
                elif isinstance(poses[0][nm], (int, float)) and nm != '_face':
                    vs = sm1([q[nm] for q in poses])
                    for i, q in enumerate(poses): q[nm] = vs[i]
    for pose in poses: frames.append(rig.draw(pose, prm))

    json.dump({'keys': keys, 'frames': frames, 'poses': poses, 'params': prm}, open(d / 'drawn_frames.json', 'w'), separators=(',', ':'))
    return frames, keys


if __name__ == '__main__':
    fr, k = run(*sys.argv[1:4]); print(len(fr), 'frames,', len(k), 'keys')
