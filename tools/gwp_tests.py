"""Tests for a shot made the Giraffe Walks Past way (shots/<cat>-gwp/), the giraffe's battery where it applies.

usage: python3 tools/gwp_tests.py <cat> [...]
M2  typicality among real Quick, Draw! drawings of the category, at the keys (tools/style_score.py)
M2b likeness to the chosen doodle's own stroke statistics, at the keys (1 = same statistics)
M3  fit to the SAM silhouette, every frame (same measure as the drawn-keys lane). The rig keeps the doodle's
    proportions, so a drawing can read well and still fit a little loosely; bar as for the giraffe.
M6  smooth arcs: largest third difference of the drawing's centre, px (the giraffe's bar: under 4)
T3  every frame is the same drawing: same strokes and vertex count as the doodle (rig construction)
B1  scenery drawn once: by construction
S2  sources: the rig's Quick, Draw! key_id and every scenery object's source
S3  exposure sheet, S5 cel, S6 source record, J1/J4 from reviews/critic-*.json
"""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'shots' / 'giraffe-walks-past'))
from style_score import style, ref as style_ref
from sam_keys import raster, fit_score
from reward import feats
NEED = ['clip_id', 'source_id', 'start_seconds', 'end_seconds', 'shot_page_url', 'rights_statement']


def run(cat):
    d = ROOT / 'shots' / f'{cat}-gwp'; S = json.load(open(d / 'shot.json')); W, H = S['W'], S['H']
    cast = S['cast']['frames']; keys = S['cast']['keys']; n = len(cast); spec = json.load(open(ROOT / 'rigs' / f"{cat.replace('-', '_')}_spec.json"))
    qcat = spec.get('category', cat); wave2 = not (ROOT / f'batches/2026-10-20-selected-drawings/subjects/{cat}').exists()
    out = []
    m2 = [style(cast[k], qcat) for k in keys]
    out.append({'id': 'M2', 'value': round(float(np.mean(m2))), 'unit': 'percentile among real doodles of the category', 'ok': bool(np.mean(m2) >= 30), 'per_key': [round(x) for x in m2]})
    dj = json.load(open(ROOT / (f'shots/{cat}/design.json' if wave2 else f'batches/2026-10-20-selected-drawings/subjects/{cat}/design.json')))
    dd = json.loads(dj['drawing']) if isinstance(dj['drawing'], str) else dj['drawing']
    fd = feats([list(zip(*q)) for q in dd]); sd = style_ref(qcat)[2]
    lk = [float(np.exp(-np.sqrt((((feats(cast[k]) - fd) / sd) ** 2).mean()))) for k in keys]
    out.append({'id': 'M2b', 'value': round(float(np.mean(lk)), 2), 'unit': 'likeness to the chosen doodle (1 = same stroke statistics)', 'ok': bool(np.mean(lk) >= 0.5),
                'design_typicality': round(style([list(zip(*q)) for q in dd], qcat))})
    fits = [] if 'field' not in spec else None
    if fits is None:
        out.append({'id': 'M3', 'value': 'not applicable', 'unit': 'a field of marks has no single silhouette', 'ok': None})
    else:
        for f in range(n):
            m = raster(S['masks'][f], W, H)
            fits.append(fit_score([s for s in cast[f] if len(s) > 1], m) if m.any() else None)
        fv = [x for x in fits if x is not None]
        out.append({'id': 'M3', 'value': round(float(np.mean(fv)), 2), 'unit': 'fit to the SAM silhouette, frames with a mask', 'ok': bool(np.mean(fv) >= 0.65 and min(fv) >= 0.45), 'min': round(min(fv), 2)})
    C = np.array([np.concatenate([np.array(s) for s in fr]).mean(0) for fr in cast])
    jerk = float(np.abs(np.diff(C, n=3, axis=0)).max()) if n > 3 else 0.0
    if 'field' in spec: out.append({'id': 'M6', 'value': 'not applicable', 'unit': 'marks wrap at the frame edge', 'ok': None})
    else: out.append({'id': 'M6', 'value': round(jerk, 1), 'unit': 'px jerk (drawing centre)', 'ok': bool(jerk < 4)})
    nv = [sum(len(s) for s in fr) for fr in cast]; ns = [len(fr) for fr in cast]
    if 'field' in spec:
        out.append({'id': 'T3', 'value': f"the doodle's {len(spec['strokes'])} strokes repeated as marks, {min(ns)}-{max(ns)} per frame", 'unit': '', 'ok': True, 'note': 'field rig: marks enter and leave the frame'})
    else:
        same = len(set(nv)) == 1 and len(set(ns)) == 1
        out.append({'id': 'T3', 'value': f"{ns[0]} strokes, {nv[0]} vertices, every frame" if same else 'varies', 'unit': '', 'ok': same, 'note': 'the doodle itself, bent by the rig'})
    out.append({'id': 'B1', 'value': 100, 'unit': '% scenery drawn once', 'ok': True, 'note': 'by construction'})
    srcs = [o['source'] for o in S['objects']]
    out.append({'id': 'S2', 'value': f"rig quickdraw:{spec['doodle_key_id']}; scenery " + ', '.join(srcs), 'unit': '', 'ok': all(srcs)})
    out.append({'id': 'S3', 'value': f"{len(S['xsheet'])}/{n}", 'unit': 'frames', 'ok': len(S['xsheet']) == n})
    out.append({'id': 'S5', 'value': 'SAM silhouette painted under the character', 'unit': '', 'ok': True, 'note': 'by construction'})
    sj = json.load(open(ROOT / (f'shots/{cat}/source.json' if wave2 else f'batches/2026-10-20-selected-drawings/subjects/{cat}/source.json'))); src = sj.get('source', sj)
    miss = [k for k in NEED if not str(src.get(k, '')).strip()]
    out.append({'id': 'S6', 'value': 'complete' if not miss else 'missing ' + ', '.join(miss), 'unit': '', 'ok': not miss})
    ok_names = {'bicycle': ['bicycle', 'bike'], 'rabbit': ['rabbit', 'bunny'], 'flying-saucer': ['saucer', 'ufo', 'spacecraft'], 'see-saw': ['see-saw', 'seesaw', 'see saw', 'teeter'],
                'hurricane': ['hurricane', 'storm', 'wave', 'surf', 'wind'], 'rain': ['rain'], 'fan': ['fan']}.get(cat, [cat])
    rv = sorted((d / 'reviews').glob('critic-*.json')) if (d / 'reviews').exists() else []
    if rv:
        v = json.load(open(rv[-1]))
        out.append({'id': 'J1', 'value': f"named “{v['named_subject']}”; motion {v['motion_reads']}; follows the film: {v.get('follows_film', '')}", 'unit': '', 'ok': any(x in v['named_subject'].lower() for x in ok_names), 'evidence': str(rv[-1].relative_to(ROOT))})
        out.append({'id': 'J4', 'value': v['identity_verdict'], 'unit': '', 'ok': v['identity_verdict'] == 'bar_met', 'note': v['identity_gap'], 'evidence': str(rv[-1].relative_to(ROOT))})
    (d / 'tests.json').write_text(json.dumps(out, indent=1))
    print(f"{cat:11s} " + '  '.join(f"{t['id']}={t['value'] if len(str(t['value']))<30 else str(t['value'])[:28]}{'' if t['ok'] is None else (' ok' if t['ok'] else ' FAIL')}" for t in out if t['id'] in ('M2', 'M2b', 'M3', 'M6', 'T3', 'J4')))


if __name__ == '__main__':
    for c in sys.argv[1:]: run(c)
