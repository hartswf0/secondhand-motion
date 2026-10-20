"""Shot tests for a drawn-keys-over-SAM shot (shots/<cat>-sam/), the Giraffe Walks Past battery where it applies.

usage: python3 tools/sam_tests.py <category> [...]
M1  recognition: read from data/m1/results.json under "<cat>" / "sam" once the browser classifier has run
M2  typicality of the character at each key, Quick, Draw!-simplified (tools/style_score.py)
M3  fit of the character to the SAM silhouette on every frame (ink inside the dilated mask × box agreement);
    bar as for the giraffe: mean at least 0.65, no frame below 0.45
M6  smooth arcs: largest third difference of the character's centre, px
T1  trace fidelity of the drawn keys (from the batch trace)
T3  share of character ink matched from key to key (worst pair)
B1  scenery drawn once: 100% by construction
S5  silhouette painted under the character (cel), so scenery cannot show through: by construction
S2, S3, S6 as for the other shots
J1, J4 kept from reviews/critic-*.json if present
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from style_score import style
from sam_keys import raster, fit_score

NEED = ['clip_id', 'source_id', 'start_seconds', 'end_seconds', 'shot_page_url', 'rights_statement']


def run(cat):
    d = ROOT / 'shots' / f'{cat}-sam'; S = json.load(open(d / 'shot.json'))
    W, H = S['W'], S['H']; cast = S['cast']['frames']; keys = S['cast']['keys']; n = len(cast)
    masks = [raster(S['masks'][f], W, H) for f in range(n)]
    out = []
    m1 = json.load(open(ROOT / 'data/m1/results.json')).get(cat, {}).get('sam')
    if m1:
        ps = [x['p'] for x in m1]
        out.append({'id': 'M1', 'value': round(float(np.mean(ps)), 2), 'unit': 'classifier p, mean of keys', 'ok': min(ps) > 0.75, 'per_key': ps, 'tops': [x['top'] for x in m1]})
    else:
        out.append({'id': 'M1', 'value': 'not run', 'unit': '', 'ok': None})
    m2 = [style(cast[k], cat) for k in keys if cast[k]]
    out.append({'id': 'M2', 'value': round(float(np.mean(m2))), 'unit': 'percentile (Quick, Draw! simplification first)', 'ok': bool(np.mean(m2) >= 30), 'per_key': [round(x) for x in m2]})
    fits = [fit_score([s for s in cast[f] if len(s) > 1], masks[f]) if masks[f].any() and cast[f] else 0.0 for f in range(n)]
    out.append({'id': 'M3', 'value': round(float(np.mean(fits)), 2), 'unit': 'fit to the SAM silhouette, every frame', 'ok': bool(np.mean(fits) >= 0.65 and min(fits) >= 0.45),
                'min': round(min(fits), 2), 'per_frame': [round(x, 2) for x in fits]})
    C = np.array([np.concatenate([np.array(s) for s in cast[f]]).mean(0) if cast[f] else [np.nan, np.nan] for f in range(n)])
    jerk = float(np.nanmax(np.abs(np.diff(C, n=3, axis=0)))) if n > 3 else 0.0
    out.append({'id': 'M6', 'value': round(jerk, 1), 'unit': 'px jerk (character centre)', 'ok': bool(jerk < 4)})
    tr = json.load(open(ROOT / 'traced/traced_keys.json'))[cat]['keys']
    rec = min(k['recall'] for k in tr); parts = min(k['parts_kept'] for k in tr)
    out.append({'id': 'T1', 'value': f'{rec:.3f} / {parts:.2f}', 'unit': 'recall / pieces kept', 'ok': rec >= 0.98 and parts >= 1})
    out.append({'id': 'T3', 'value': f"{min(S['matched_ink']):.2f}", 'unit': 'worst key pair, share of character ink matched', 'ok': min(S['matched_ink']) >= 0.7})
    out.append({'id': 'B1', 'value': 100, 'unit': '% scenery strokes held (drawn once)', 'ok': True, 'note': 'by construction'})
    out.append({'id': 'S5', 'value': 'SAM silhouette painted under the character', 'unit': '', 'ok': True, 'note': 'by construction'})
    out.append({'id': 'S2', 'value': 'look-lane keys (image model, critic-approved) + SAM', 'unit': '', 'ok': True})
    out.append({'id': 'S3', 'value': f"{len(S['xsheet'])}/{n}", 'unit': 'frames', 'ok': len(S['xsheet']) == n})
    src = json.load(open(ROOT / f'batches/2026-10-20-selected-drawings/subjects/{cat}/source.json'))['source']
    miss = [k for k in NEED if not str(src.get(k, '')).strip()]
    out.append({'id': 'S6', 'value': 'complete' if not miss else 'missing ' + ', '.join(miss), 'unit': '', 'ok': not miss})
    ok_names = {'bicycle': ['bicycle', 'bike'], 'rabbit': ['rabbit', 'bunny']}.get(cat, [cat])
    for p in sorted((d / 'reviews').glob('critic-*.json')) if (d / 'reviews').exists() else []:
        v = json.load(open(p)); out = [t for t in out if t['id'] not in ('J1', 'J4')]
        named = any(x in v['named_subject'].lower() for x in ok_names)
        out.append({'id': 'J1', 'value': f"named “{v['named_subject']}”; motion {v['motion_reads']}" + (f" at frames {', '.join(map(str, v['broken_frames']))}" if v['broken_frames'] else ''),
                    'unit': '', 'ok': named, 'evidence': str(p.relative_to(ROOT))})
        out.append({'id': 'J4', 'value': v['identity_verdict'], 'unit': '', 'ok': v['identity_verdict'] == 'bar_met', 'note': v['identity_gap'], 'evidence': str(p.relative_to(ROOT))})
    (d / 'tests.json').write_text(json.dumps(out, indent=1))
    print(f"{cat:11s} " + '  '.join(f"{t['id']}={t['value']}{'' if t['ok'] is None else (' ok' if t['ok'] else ' FAIL')}" for t in out if t['id'] in ('M1', 'M2', 'M3', 'M6', 'T3', 'J1', 'J4')))


if __name__ == '__main__':
    for c in sys.argv[1:]: run(c)
