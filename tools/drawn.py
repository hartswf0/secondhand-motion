"""Drawn keys: key drawings made by hand over the footage, on top of the rig.

The rig bends the chosen doodle; it cannot turn a pig toward the camera, open a giraffe's jaw or put a bow in a
cellist's hand. A drawn key is the doodle at one frame redrawn by moving its own points (same strokes, same
points, so it stays the same drawing and can be in-betweened), plus optional extra strokes in the doodle's hand
for a part the doodle never drew (a bow, eyestalks, a second ear when the head turns).

Files, one per drawn frame: shots/<slug>/drawn/k###.json
  {"why": "what happens at this frame and why it is a key (contact, extreme, turn, the line)",
   "strokes": [[[x, y], ...], ...],      # same stroke count and points per stroke as the rig drawing at that frame
   "extra": {"name": [[x, y], ...]}}     # optional added strokes, frame pixels
Optional shots/<slug>/drawn/xsheet.json: {"line": frame, "line_why": "...", "holds": [[f0, f1], ...], "ease": "smooth" | "linear"}
("linear" moves at an even rate between keys: for steady travel such as a train climbing; the default eases in and out of every key)

How a shot uses them (apply()): at each drawn frame the drawing is replaced by the drawn key. Between keys the
change from the rig (drawn minus rig, point by point) is eased from one key to the next, so in-betweens are the
rig's motion plus the drawn changes, and undrawn rig keys pull the change back to zero. A hold keeps the drawing
of its first frame, moved only by the rig's root motion, until its last frame. Extra strokes are kept relative to
the drawing's centre and eased between the keys that have them; they show from their first key to their last.
"""
import json
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent


def ease(t): return t * t * (3 - 2 * t)


def resample(s, n):
    s = np.array(s, float)
    if len(s) == n: return s
    if len(s) == 1: return np.repeat(s, n, 0)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(s, axis=0).T))]; t = np.linspace(0, d[-1], n)
    return np.c_[np.interp(t, d, s[:, 0]), np.interp(t, d, s[:, 1])]


def load(slug):
    d = ROOT / 'shots' / slug / 'drawn'
    K = {int(p.stem[1:]): json.load(open(p)) for p in sorted(d.glob('k[0-9][0-9][0-9].json'))} if d.exists() else {}
    X = json.load(open(d / 'xsheet.json')) if (d / 'xsheet.json').exists() else {}
    return {f: k for f, k in K.items() if k.get('strokes')}, X


def apply(slug, frames, rig_keys):
    """frames: list (per frame) of strokes from the rig. Returns (frames, all key frames, drawn key frames)."""
    K, X = load(slug)
    if not K: return frames, rig_keys, []
    ez = (lambda t: t) if X.get('ease') == 'linear' else ease
    n = len(frames); rig = [[np.array(s, float) for s in fr] for fr in frames]
    delta = {}
    for f, k in K.items():
        if f >= n: continue
        dr = k['strokes']
        if len(dr) != len(rig[f]): raise SystemExit(f'{slug} k{f:03d}: {len(dr)} strokes, the rig drawing has {len(rig[f])}')
        delta[f] = [resample(dr[i], len(rig[f][i])) - rig[f][i] for i in range(len(dr))]
    anchors = sorted(set(delta) | {k for k in rig_keys if k not in delta})
    zero = lambda f: [np.zeros_like(s) for s in rig[f]]
    D = {f: delta.get(f, zero(f)) for f in anchors}
    out = []
    for f in range(n):
        a = max([k for k in anchors if k <= f], default=anchors[0]); b = min([k for k in anchors if k >= f], default=anchors[-1])
        t = 0 if a == b else ez((f - a) / (b - a))
        out.append([rig[f][i] + D[a][i] * (1 - t) + D[b][i] * t for i in range(len(rig[f]))])
    for h0, h1 in X.get('holds', []):   # a hold: the drawing of h0, carried by the root motion only
        c0 = np.concatenate(out[h0]).mean(0)
        for f in range(h0 + 1, min(h1, n - 1) + 1):
            c = np.concatenate(rig[f]).mean(0) - np.concatenate(rig[h0]).mean(0)
            out[f] = [s + c for s in out[h0]]
    # extra strokes, relative to the drawing's centre
    names = sorted({nm for k in K.values() for nm in k.get('extra', {})})
    cen = [np.concatenate(fr).mean(0) for fr in out]
    for nm in names:
        ks = sorted(f for f, k in K.items() if nm in k.get('extra', {}) and f < n)
        m = max(len(K[f]['extra'][nm]) for f in ks)
        rel = {f: resample(K[f]['extra'][nm], m) - cen[f] for f in ks}
        for f in range(ks[0], ks[-1] + 1):
            a = max(k for k in ks if k <= f); b = min(k for k in ks if k >= f); t = 0 if a == b else ez((f - a) / (b - a))
            out[f] = out[f] + [rel[a] * (1 - t) + rel[b] * t + cen[f]]
    frames = [[np.round(s, 1).tolist() for s in fr] for fr in out]
    return frames, sorted(set(rig_keys) | set(delta)), sorted(delta)
