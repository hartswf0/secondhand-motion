"""Where each drawn key sits in the animated excerpt.

The drawn keys were drawn over source-key-<i>.png, stills cut from the original film by a seek that does
not land on the same frame as the excerpt we animate, and the camera in several films zooms. So a drawing
in source-key coordinates is not in excerpt coordinates. For each key this finds the excerpt frame that the
still matches best (within +-6 frames of the key time) and the similarity transform (scale, rotation,
shift) from still to that frame, by ORB features and RANSAC, checked by the photometric error after warping.

usage: python3 tools/key_align.py <cat> [...]  -> shots/<cat>-sam/key_align.json
"""
import json, sys
from pathlib import Path
import numpy as np, cv2
ROOT = Path(__file__).resolve().parent.parent
B = ROOT / 'batches/2026-10-20-selected-drawings/subjects'


def fit(a, b):
    orb = cv2.ORB_create(1500); ka, da = orb.detectAndCompute(a, None); kb, db = orb.detectAndCompute(b, None)
    if da is None or db is None or len(ka) < 8 or len(kb) < 8: return None, 0
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(da, db)
    if len(m) < 8: return None, 0
    pa = np.float32([ka[x.queryIdx].pt for x in m]); pb = np.float32([kb[x.trainIdx].pt for x in m])
    M, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=3.0, maxIters=4000)
    return M, int(inl.sum()) if inl is not None else 0


def err(a, b, M):
    H, W = b.shape; w = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=-1)
    ok = w >= 0; return float(np.abs(w[ok] - b[ok]).mean()) if ok.mean() > 0.5 else 99.0


def run(cat):
    d = ROOT / 'shots' / f'{cat}-sam'; clip = json.load(open(d / 'clip.json')); n = clip['n']
    G = lambda p: cv2.GaussianBlur(cv2.imread(str(p), 0), (3, 3), 0)
    out = []
    for i, k in enumerate(clip['keys']):
        a = G(B / cat / f'source-key-{i}.png'); af = a.astype(np.float32)
        best = None
        for f in range(max(0, k - 6), min(n, k + 7)):
            b = G(d / 'frames' / f'f{f:03d}.jpg'); bf = b.astype(np.float32)
            cands = [np.float32([[1, 0, 0], [0, 1, 0]])]
            M, inl = fit(a, b)
            if M is not None: cands.append(M.astype(np.float32))
            for M in cands:
                e = err(af, bf, M)
                if best is None or e < best[0]: best = (e, f, M, inl)
        e, f, M, inl = best; s = float(np.hypot(M[0, 0], M[1, 0]))
        out.append({'key': i, 'key_frame': k, 'frame': f, 'M': M.tolist(), 'scale': round(s, 3), 'shift': [round(float(M[0, 2]), 1), round(float(M[1, 2]), 1)],
                    'error_after': round(e, 2), 'error_identity_at_key': round(err(af, G(d / 'frames' / f'f{k:03d}.jpg').astype(np.float32), np.float32([[1, 0, 0], [0, 1, 0]])), 2), 'inliers': inl})
    (d / 'key_align.json').write_text(json.dumps(out, indent=1))
    print(cat, [(o['key_frame'], o['frame'], o['scale'], o['shift'], o['error_identity_at_key'], o['error_after']) for o in out])


if __name__ == '__main__':
    for c in sys.argv[1:]: run(c)
