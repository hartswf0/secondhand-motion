"""First guess at rabbit/dog-style profile pose points from a SAM silhouette (Giraffe Walks Past step 4).
A starting point to correct by eye, not a drawing. face: +1 facing right, -1 facing left."""
import numpy as np


def pts(mask, face):
    ys, xs = np.nonzero(mask)
    if not len(xs): return None
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max(); w, h = x1 - x0, y1 - y0
    front = (lambda x: x >= x0 + w * 0.5) if face > 0 else (lambda x: x <= x0 + w * 0.5)
    fx = lambda a: a if face > 0 else -a
    def extreme(sel, key):
        i = np.where(sel)[0]
        if not len(i): return None
        j = i[np.argmax(key[i])]; return [float(xs[j]), float(ys[j])]
    top_band = ys < y0 + h * 0.5
    nose = extreme(top_band & (ys > y0 + h * 0.15), fx(xs).astype(float))
    ear2 = extreme(np.array([front(x) for x in xs]), -ys.astype(float))
    ear1 = extreme(np.array([not front(x) for x in xs]) & (np.abs(xs - (ear2[0] if ear2 else 0)) < w * 0.35), -ys.astype(float)) or ear2
    mid = (ys > y0 + h * 0.55) & (ys < y0 + h * 0.85)
    chest = extreme(mid & np.array([front(x) for x in xs]), fx(xs).astype(float))
    tail = extreme(mid, -fx(xs).astype(float))
    bot = ys > y0 + h * 0.8
    paw = extreme(bot & np.array([front(x) for x in xs]), ys.astype(float) + fx(xs) * 0.3)
    foot = extreme(bot & np.array([not front(x) for x in xs]), ys.astype(float) - fx(xs) * 0.3)
    back = extreme(np.array([not front(x) for x in xs]) & (ys > y0 + h * 0.25), -ys.astype(float))
    head = [nose[0] - face * w * 0.18, nose[1] - h * 0.12]
    chin = [nose[0] - face * 8, nose[1] + 14]
    belly = [(paw[0] + foot[0]) / 2, max(paw[1], foot[1]) - h * 0.12]
    r = lambda p: [round(p[0]), round(p[1])]
    return {k: r(v) for k, v in dict(ear1=ear1, ear2=ear2, head=head, nose=nose, chin=chin, chest=chest, paw=paw, belly=belly, foot=foot, tail=tail, back=back).items()}
