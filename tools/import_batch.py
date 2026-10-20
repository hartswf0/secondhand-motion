"""Import a look-lane batch (raster keys + reviews) as lots on the rack, and score what can be scored.

usage: python3 tools/import_batch.py batches/<batch> traced/traced_keys.json [--wave N]

For each subject in the batch, writes shots/<slug>/item.json, source.json (copied) and tests.json with
  S6 source record complete   from the batch's source.json
  J4 keeps the doodle         from the selected revision's review verdict
  B1 background holds         from the traced keys' layer split
  T1 trace keeps the drawing  from the traced keys' scores
and every other active test marked not run. item.json and source.json are kept if present; tests.json
is rewritten from evidence each run.
"""
import argparse, glob, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from new_subject import next_lot, slug

NEED = ['clip_id', 'source_id', 'start_seconds', 'end_seconds', 'shot_page_url', 'rights_statement']


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('batch'); ap.add_argument('traced'); ap.add_argument('--wave', type=int, default=1)
    a = ap.parse_args()
    B = ROOT / a.batch; tr = json.load(open(ROOT / a.traced)); val = json.load(open(B / 'validation.json'))
    reg = [t for t in json.load(open(ROOT / 'tests/registry.json'))['tests'] if t['status'] == 'active']
    rel = B.relative_to(ROOT).as_posix()
    for s in val['subjects']:
        cat = s['category']; d = ROOT / 'shots' / slug(cat); d.mkdir(parents=True, exist_ok=True)
        src = json.load(open(B / 'subjects' / cat / 'source.json'))
        if not (d / 'source.json').exists(): shutil.copy(B / 'subjects' / cat / 'source.json', d / 'source.json')
        miss = [k for k in NEED if not str(src['source'].get(k, '')).strip()]
        rv = json.load(open(B / s['review'])); verdict = rv.get('verdict')
        keys = tr[cat]['keys']
        rec = min(k['recall'] for k in keys); parts = min(k['parts_kept'] for k in keys)
        still = sum(k['n_strokes'] - k['char_strokes'] for k in keys) / sum(k['n_strokes'] for k in keys)
        res = {
            'S6': {'value': 'complete' if not miss else 'missing ' + ', '.join(miss), 'unit': '', 'ok': not miss},
            'J4': {'value': f"{verdict} ({s['selected_revision']})", 'unit': '', 'ok': verdict == 'bar_met', 'evidence': s['review']},
            'B1': {'value': round(still * 100), 'unit': '% strokes held', 'ok': still >= 0.9},
            'T1': {'value': f'{rec:.3f} / {parts:.2f}', 'unit': 'recall / pieces kept', 'ok': rec >= 0.98 and parts >= 1},
        }
        mt = ROOT / 'traced/matches.json'
        if mt.exists():
            share = json.load(open(mt))[cat]['matched_ink']
            res['T3'] = {'value': f'{min(share):.2f}', 'unit': 'worst key pair, share of ink matched', 'ok': min(share) >= 0.7}
        m2 = d / 'm2.json'
        if m2.exists():
            j = json.load(open(m2)); res['M2'] = {k: j[k] for k in ('value', 'unit', 'ok') if k in j}
            if 'note' in j: res['M2']['note'] = j['note']
        tests = [{'id': t['id'], **res.get(t['id'], {'value': 'not run', 'unit': '', 'ok': None})} for t in reg]
        (d / 'tests.json').write_text(json.dumps(tests, indent=1))
        n_rev = len(glob.glob(str(B / 'reviews' / f'{cat}-v*.json')))
        if not (d / 'item.json').exists():
            sj = src['source']
            item = {'lot': next_lot(), 'id': slug(cat), 'kind': 'subject', 'title': cat.capitalize(), 'category': cat, 'wave': a.wave,
                    'lane': 'look', 'stage': 5, 'status': 'in progress', 'added': '2026-10-20',
                    'blurb': f"Four keys from {sj.get('source_title') or 'an archive film'}, {n_rev} review rounds. Traced; background redrawn per key.",
                    'cover': f'{rel}/subjects/{cat}/art-key-1.png', 'cover_alt': f'{rel}/subjects/{cat}/source-key-1.png',
                    'links': [{'label': 'Traced keys', 'href': f'pages/traced-keys.html#{cat}'},
                              {'label': 'Held keys video', 'href': f'{rel}/subjects/{cat}/held-key-comparison.mp4'},
                              {'label': 'Archive shot', 'href': sj.get('shot_page_url')}],
                    'tests': f'shots/{slug(cat)}/tests.json', 'tags': ['look lane', 'traced', f'{n_rev} reviews']}
            (d / 'item.json').write_text(json.dumps(item, indent=1))
        print(cat, {k: v['ok'] for k, v in res.items()})


if __name__ == '__main__':
    main()
