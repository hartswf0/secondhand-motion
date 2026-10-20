"""Pose the doodle rig toward a generated key: the image model drew each key in the doodle's identity over
the source pose; this finds the rig pose whose lines lie closest to that key's traced lines (symmetric
chamfer distance on distance transforms), starting from the key's bounding box. A starting point that the
agent then corrects by eye on the grid (tools/key_grid.py --target), as the giraffe's autopose was.

usage: python3 rigs/fit_to_key.py <cat> <shot_dir> <traced.json> <scale> <dx> <dy>   (key -> frame: x*scale+dx)
writes <shot_dir>/pose_fit.json {frame: pose}
"""
import json, sys, importlib.util
from pathlib import Path
import numpy as np, cv2
from scipy.optimize import minimize


def raster(strokes, W, H, w=2):
    m = np.zeros((H, W), np.uint8)
    for s in strokes:
        if len(s) > 1: cv2.polylines(m, [np.round(np.array(s)).astype(np.int32)], False, 1, w)
    return m


def chamfer(a_strokes, B_dt, B_pts, W, H):
    A = raster(a_strokes, W, H); A_dt = cv2.distanceTransform(1 - A, cv2.DIST_L2, 3)
    pa = np.argwhere(A)
    if not len(pa): return 1e6
    d1 = B_dt[np.clip(pa[:, 0], 0, H - 1), np.clip(pa[:, 1], 0, W - 1)].mean()
    d2 = A_dt[B_pts[:, 0], B_pts[:, 1]].mean()
    return float(np.minimum(d1, 40).mean() + np.minimum(d2, 40))


def fit(cat, d, traced, sc, dx, dy):
    d = Path(d); root = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location('rig', root / f'{cat}.py'); rig = importlib.util.module_from_spec(spec); spec.loader.exec_module(rig)
    sp = json.load(open(root / f'{cat}_spec.json')); clip = json.load(open(d / 'clip.json')); W, H = clip['W'], clip['H']
    T = json.load(open(traced)); names = [n for n in sp['anchors'] if n in sum([[p['aim'][0], p['aim'][1]] for p in sp['parts']], []) + sp['root']]
    names = list(dict.fromkeys(names)); out = {}
    for i, k in enumerate(T['keys']):
        strokes = [[[x * sc + dx, y * sc + dy] for x, y in s] for s in k['strokes']]
        B = raster(strokes, W, H); B_dt = cv2.distanceTransform(1 - B, cv2.DIST_L2, 3); B_pts = np.argwhere(B)
        P = np.concatenate([np.array(s) for s in strokes]); x0, y0 = P.min(0); x1, y1 = P.max(0)
        A = np.array([sp['anchors'][n] for n in names], float); a0, a1 = A.min(0), A.max(0)
        best = None
        for flip in (False, True):
            Af = A.copy()
            if flip: Af[:, 0] = 255 - Af[:, 0]
            init = (Af - Af.min(0)) / np.maximum(Af.max(0) - Af.min(0), 1) * [x1 - x0, y1 - y0] + [x0, y0]
            def f(v):
                pose = {n: [float(v[2 * j]), float(v[2 * j + 1])] for j, n in enumerate(names)}
                return chamfer(rig.draw(pose, {}), B_dt, B_pts, W, H)
            r = minimize(f, init.ravel(), method='Powell', options={'maxiter': 3000, 'xtol': 0.5, 'ftol': 0.01})
            if best is None or r.fun < best.fun: best = r
        out[str(clip['keys'][i])] = {n: [round(float(best.x[2 * j]), 1), round(float(best.x[2 * j + 1]), 1)] for j, n in enumerate(names)}
        print(cat, 'key', i + 1, 'frame', clip['keys'][i], 'chamfer', round(best.fun, 2), flush=True)
    json.dump(out, open(d / 'pose_fit.json', 'w'), indent=0)


if __name__ == '__main__':
    fit(sys.argv[1], sys.argv[2], sys.argv[3], *map(float, sys.argv[4:7]))
