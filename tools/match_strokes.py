"""In-between traced keys by stroke correspondence: the first motion for the look lane.

For each pair of consecutive keys, every stroke is resampled to N points along its length and matched
to a stroke in the next key (Hungarian assignment on mean point distance, either direction allowed).
Keys are first aligned by the translation that best overlays their ink (the subject or camera moved).
A match is kept only when the strokes are close in place and length; the page interpolates kept
matches and swaps unmatched strokes at the midpoint, the way replacement animation would.
No physics: feet slide, bodies stretch. That is what the rig fit (stage 6) is for.

usage: python3 tools/match_strokes.py traced/traced_keys.json batches/<batch> traced/matches.json
Writes, per subject: key times, resampled strokes per key, matches per key pair, and
  matched_ink: share of each key pair's ink carried by matched strokes (higher = smoother)
"""
import json, math, sys
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment

N = 16


def resample(s, n=N):
    a = np.array(s, float)
    if len(a) == 1: a = np.vstack([a, a])
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(a, axis=0).T))]
    if d[-1] == 0: return np.repeat(a[:1], n, 0)
    t = np.linspace(0, d[-1], n)
    return np.c_[np.interp(t, d, a[:, 0]), np.interp(t, d, a[:, 1])]


def length(a): return float(np.hypot(*np.diff(a, axis=0).T).sum())


def shift(A, B, W, H):
    """Translation that best lays A's ink onto B's (chamfer distance, coarse grid then fine)."""
    from scipy.spatial import cKDTree
    pa = np.concatenate(A); tb = cKDTree(np.concatenate(B))
    cost = lambda t: float(np.minimum(tb.query(pa + t)[0], 30).mean())
    best = min(((cost(np.array([dx, dy])), dx, dy) for dx in np.arange(-W / 2, W / 2 + 1, W / 24) for dy in np.arange(-H / 3, H / 3 + 1, H / 18)))
    _, bx, by = best
    for step in (W / 48, W / 96, 1):
        best = min(((cost(np.array([bx + dx, by + dy])), bx + dx, by + dy) for dx in (-step, 0, step) for dy in (-step, 0, step)))
        _, bx, by = best
    return np.array([bx, by]) if cost(np.array([bx, by])) < cost(np.zeros(2)) - 0.5 else np.zeros(2)


def match(A, B, W, H=None):
    """A, B: lists of resampled strokes. Returns [(i, j, reversed)], lengths, and the shift applied to A."""
    t = shift(A, B, W, H or W * 0.75)
    A = [a + t for a in A]
    na, nb = len(A), len(B)
    C = np.full((na, nb), 1e6); R = np.zeros((na, nb), bool)
    LA = np.array([length(a) for a in A]); LB = np.array([length(b) for b in B])
    for i, a in enumerate(A):
        for j, b in enumerate(B):
            f = np.hypot(*(a - b).T).mean(); r = np.hypot(*(a - b[::-1]).T).mean()
            ratio = max(LA[i], LB[j], 1) / max(min(LA[i], LB[j]), 1)
            C[i, j] = min(f, r) * (1 + 0.5 * (ratio - 1)); R[i, j] = r < f
    rows, cols = linear_sum_assignment(C)
    limit = 0.08 * W                                  # farther than 8% of frame width is not the same stroke
    return [(int(i), int(j), bool(R[i, j])) for i, j in zip(rows, cols) if C[i, j] < limit], LA, LB, t


def main(traced, batch, out):
    T = json.load(open(traced)); res = {}
    for cat, e in T.items():
        src = json.load(open(Path(batch) / 'subjects' / cat / 'source.json'))
        prev = json.load(open(Path(batch) / 'subjects' / cat / 'preview-data.json'))
        keys = [[resample(s) for s in k['strokes']] for k in e['keys']]
        pairs, share = [], []
        for a in range(len(keys) - 1):
            m, LA, LB, t = match(keys[a], keys[a + 1], e['W'], e['H'])
            ink = (sum(LA[i] for i, _, _ in m) + sum(LB[j] for _, j, _ in m)) / (LA.sum() + LB.sum())
            pairs.append(m); share.append(round(float(ink), 3))
        res[cat] = {'W': e['W'], 'H': e['H'], 'fps': prev.get('fps', 12), 'duration': prev.get('duration'), 'key_times': src['key_times'],
                    'keys': [[[[round(x, 1), round(y, 1)] for x, y in s] for s in k] for k in keys],
                    'matches': pairs, 'matched_ink': share}
        print(f'{cat:11s} matched ink per key pair {share}')
    json.dump(res, open(out, 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
