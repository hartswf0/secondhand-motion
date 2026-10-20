"""Put a new subject on the rack: scaffold shots/<slug>/ so an agent can pick it up.

usage: python3 tools/new_subject.py <category> [--wave N] [--no-doodle]

Writes
  shots/<slug>/item.json        the lot: number, status, stage, cover, links (read by the index)
  shots/<slug>/candidates.json  the category's archive shots from dataset/clips.csv, best first
  shots/<slug>/tests.json       every active test in tests/registry.json, marked not run
  shots/<slug>/doodle.svg       one real Quick, Draw! drawing of the category, as the lot's cover
  shots/<slug>/README.md        what to do next (points at AGENTS.md)
Existing files are never overwritten.
"""
import argparse, csv, json, subprocess, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def slug(c): return c.lower().replace(' ', '-')


def next_lot():
    lots = [json.load(open(p))['lot'] for p in lot_files()]
    n = max([int(l.split('-')[1]) for l in lots] or [0]) + 1
    return f'SM-{n:04d}'


def lot_files():
    return sorted(list(ROOT.glob('shots/*/item.json')) + list(ROOT.glob('batches/*/item.json')) + list(ROOT.glob('data/lots/*.json')))


def candidates(category):
    rows = [r for r in csv.DictReader(open(ROOT / 'dataset/clips.csv')) if r['category'] == category]
    rows.sort(key=lambda r: -float(r['score']))
    keep = ['rank', 'score', 'clip_id', 'source_title', 'source_year', 'start_seconds', 'end_seconds', 'duration_seconds',
            'color_mode', 'aspect_ratio', 'page_url', 'thumbnail_url', 'video_url']
    return [{k: r[k] for k in keep} for r in rows]


def doodle(category):
    """First recognized drawing in the category's simplified file (CC BY 4.0, Google Creative Lab)."""
    url = f"https://storage.googleapis.com/quickdraw_dataset/full/simplified/{category.replace(' ', '%20')}.ndjson"
    try:
        raw = subprocess.run(['curl', '-sSf', '-r', '0-200000', url], capture_output=True, check=True, timeout=60).stdout.decode()
    except Exception as e:
        print('  no doodle:', e, file=sys.stderr); return None, None
    for line in raw.splitlines()[:-1]:
        r = json.loads(line)
        if not r['recognized'] or not 3 <= len(r['drawing']) <= 12: continue
        paths = ' '.join('M' + ' L'.join(f'{x} {y}' for x, y in zip(s[0], s[1])) for s in r['drawing'])
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-12 -12 280 280"><path d="{paths}" fill="none" stroke="#161412" '
               f'stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>')
        return svg, r['key_id']
    return None, None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('category'); ap.add_argument('--wave', type=int, default=None)
    ap.add_argument('--no-doodle', action='store_true'); a = ap.parse_args()
    cats = {r['category'] for r in csv.DictReader(open(ROOT / 'dataset/categories.csv'))}
    if a.category not in cats: sys.exit(f'{a.category!r} is not one of the 345 categories')
    d = ROOT / 'shots' / slug(a.category); d.mkdir(parents=True, exist_ok=True)
    def put(name, text):
        p = d / name
        if p.exists(): print('  kept', p.relative_to(ROOT)); return
        p.write_text(text); print('  wrote', p.relative_to(ROOT))
    cand = candidates(a.category)
    put('candidates.json', json.dumps({'category': a.category, 'note': 'Ranked by the archive search score. Watch before choosing: see AGENTS.md step 1.', 'clips': cand}, indent=1))
    reg = json.load(open(ROOT / 'tests/registry.json'))['tests']
    put('tests.json', json.dumps([{'id': t['id'], 'value': 'not run', 'unit': '', 'ok': None} for t in reg if t['status'] == 'active'], indent=1))
    key_id = None
    if not a.no_doodle and not (d / 'doodle.svg').exists():
        svg, key_id = doodle(a.category)
        if svg: put('doodle.svg', svg)
    put('README.md', f'# {a.category}\n\nQueued. Run the agent prompt in `AGENTS.md` with `{{CATEGORY}}` = `{a.category}`.\n'
                     f'Start from `candidates.json` ({len(cand)} archive shots). Write everything into this folder.\n')
    if not (d / 'item.json').exists():
        item = {'lot': next_lot(), 'id': slug(a.category), 'kind': 'subject', 'title': a.category.capitalize(), 'category': a.category,
                'wave': a.wave, 'lane': 'queue', 'stage': -1, 'status': 'queued', 'added': date.today().isoformat(),
                'blurb': f'{len(cand)} archive shots to watch. Best match: {cand[0]["source_title"]} ({cand[0]["score"][:5]}).' if cand else 'No archive shots found.',
                'cover': f'shots/{slug(a.category)}/doodle.svg' if (d / 'doodle.svg').exists() else None,
                'cover_credit': f'Quick, Draw! key_id {key_id}, CC BY 4.0' if key_id else None,
                'links': [{'label': 'Candidates', 'href': f'shots/{slug(a.category)}/candidates.json'}],
                'tests': f'shots/{slug(a.category)}/tests.json', 'tags': ['queued']}
        put('item.json', json.dumps(item, indent=1))


if __name__ == '__main__':
    main()
