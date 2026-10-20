"""M2 'Looks hand-drawn' for any category: how typical a drawing's stroke statistics are among real
recognized Quick, Draw! drawings of the same category, after the same simplification Quick, Draw!
applies to its own data (percentile of mean distance to 25 nearest
neighbours; 50 is a median real doodle, 100 the most typical).

usage: python3 tools/style_score.py traced/traced_keys.json
Scores only subjects whose keys show the character alone (listed in SUBJECT_ONLY, an agent judgment
made by looking at the keys). Every other subject is left 'not run': its keys include scenery, and
separating character from scenery needs a mask (pipeline stage 1), which these clips do not have yet.
Writes shots/<slug>/m2.json; tools/import_batch.py folds it into tests.json.
"""
import json, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'shots' / 'giraffe-walks-past'))
from reward import feats  # same features as the giraffe shot's M2

SUBJECT_ONLY = {
    'cat': 'head and shoulders fill the frame; no scenery strokes',
    'duck': 'duck alone with one ground line, which Quick, Draw! ducks often have too',
    'giraffe': 'head and neck close-up; every stroke is the giraffe',
}
_refs = {}


def ref(cat):
    if cat not in _refs:
        rows = [json.loads(l) for l in open(ROOT / f'data/quickdraw/{cat}.part').read().splitlines()[:-1]]
        F = np.array([feats([list(zip(*s)) for s in r['drawing']]) for r in rows if r['recognized']])
        mu, sd = F.mean(0), F.std(0) + 1e-6; Z = (F - mu) / sd
        D = np.sqrt(((Z[:1500, None, :] - Z[None, :, :]) ** 2).sum(-1)); D.sort(1)
        _refs[cat] = (Z, mu, sd, np.sort(D[:, 1:26].mean(1)), len(F))
    return _refs[cat]


def qd_simplify(strokes):
    """The Quick, Draw! simplified files were made this way: align to the top-left, scale the longer
    side to 255, then Ramer-Douglas-Peucker with epsilon 2. Doing the same here compares like with like."""
    sys.path.insert(0, str(ROOT / 'tools')); from trace_keys import rdp
    pts = np.array([p for s in strokes for p in s], float); lo = pts.min(0); sc = 255 / max(np.ptp(pts[:, 0]), np.ptp(pts[:, 1]), 1)
    return [rdp([[(x - lo[0]) * sc, (y - lo[1]) * sc] for x, y in s], 2.0) for s in strokes]


def style(strokes, cat):
    Z, mu, sd, real_knn, _ = ref(cat)
    z = (feats(qd_simplify(strokes)) - mu) / sd
    d = np.sqrt(((Z - z) ** 2).sum(1)); d.sort()
    return float(100 * (1 - np.searchsorted(real_knn, d[:25].mean()) / len(real_knn)))


def main(path):
    T = json.load(open(path))
    for cat, e in T.items():
        out = ROOT / 'shots' / cat / 'm2.json'
        if cat not in SUBJECT_ONLY:
            out.write_text(json.dumps({'id': 'M2', 'value': 'not run', 'unit': '', 'ok': None,
                                       'note': 'keys include scenery; needs a character mask (stage 1) first'}, indent=1)); continue
        s = [style(k['strokes'], cat) for k in e['keys']]
        n = [k['n_strokes'] for k in e['keys']]
        out.write_text(json.dumps({'id': 'M2', 'value': round(float(np.mean(s))), 'unit': 'percentile, mean of 4 keys', 'ok': bool(np.mean(s) >= 30),
                                   'per_key': [round(x) for x in s], 'strokes_per_key': n, 'reference': f'{ref(cat)[4]} recognized {cat} doodles',
                                   'why_scored': SUBJECT_ONLY[cat]}, indent=1))
        print(f'{cat:8s} M2 per key {[round(x) for x in s]}  strokes {n}')
    # the motion lane, measured the same way, so the two lanes can be compared on one scale
    P = json.load(open(ROOT / 'shots/giraffe-walks-past/pose_agent_v5.json')); keys = sorted(int(k) for k in P)
    F = json.load(open(ROOT / 'shots/giraffe-walks-past/drawn_frames_v5.json'))
    s = [style(F[k]['strokes'], 'giraffe') for k in keys]
    (ROOT / 'shots/giraffe-walks-past/m2-simplified.json').write_text(json.dumps({'id': 'M2', 'value': round(float(np.mean(s))), 'per_key': [round(x) for x in s],
        'strokes_per_key': [len(F[k]['strokes']) for k in keys], 'note': 'same measure as tools/style_score.py (Quick, Draw! simplification first); tests.py reports the unsimplified 16'}, indent=1))
    print('giraffe shot keys, same measure', [round(x) for x in s])


if __name__ == '__main__':
    main(sys.argv[1])
