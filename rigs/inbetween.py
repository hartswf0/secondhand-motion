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
        if scale_k is not None and not np.isnan(sm_area[f]): pose['_scale'] = float(scale_k * sm_area[f])
        for nm, v in A.items():   # number-valued pose entries (a wing's open amount) ease between the keys
            if isinstance(v, (int, float)) and nm in B:
                pose[nm] = float(v + (B[nm] - v) * (t * t * (3 - 2 * t)))
        poses.append(pose); frames.append(rig.draw(pose, prm))
    json.dump({'keys': keys, 'frames': frames, 'poses': poses, 'params': prm}, open(d / 'drawn_frames.json', 'w'), separators=(',', ':'))
    return frames, keys


if __name__ == '__main__':
    fr, k = run(*sys.argv[1:4]); print(len(fr), 'frames,', len(k), 'keys')
