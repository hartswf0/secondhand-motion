"""The reel: every Giraffe-Walks-Past shot in one player (pages/reel.html).

Each shot's drawing data stays in its own shots/<slug>-gwp/shot.json and is fetched when needed, so the page
stays small. The index embedded here carries what the list and captions need: title, film, frame count, the line
(the one beat the shot exists for), drawn keys and the latest blind-critic verdict.

usage: python3 tools/build_reel.py      (also called from tools/build_pages.py)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def latest_review(gwp):
    rv = sorted(gwp.glob('reviews/critic-*.json'), key=lambda p: int(p.stem.split('-')[-1]))
    return (json.load(open(rv[-1])), len(rv)) if rv else ({}, 0)


def index():
    out = []
    for f in sorted(ROOT.glob('shots/*-gwp/shot.json')):
        gwp = f.parent; slug = gwp.name[:-4]
        S = json.load(open(f))
        v, rounds = latest_review(gwp)
        drawn = ROOT / 'shots' / slug / 'drawn'
        X = json.load(open(drawn / 'xsheet.json')) if (drawn / 'xsheet.json').exists() else {}
        base = json.load(open(drawn / 'baseline.json')) if (drawn / 'baseline.json').exists() else {}
        out.append({'slug': slug, 'title': slug.replace('-', ' ').capitalize(), 'film': S['source'].get('film', ''),
                    'url': S['source'].get('url', ''), 'n': len(S['cast']['frames']), 'fps': S['fps'], 'W': S['W'], 'H': S['H'],
                    'line': X.get('line'), 'line_why': X.get('line_why', ''), 'drawn': S['cast'].get('drawn_keys', []),
                    'keys': S['cast']['keys'], 'verdict': v.get('verdict', ''), 'score': v.get('motion_score'),
                    'identity': v.get('identity_verdict', ''), 'gap': v.get('primary_gap', ''), 'rounds': rounds,
                    'baseline': base.get('motion_score')})
    return out


def build(page):
    """page: tools/build_pages.page (fills __HEAD__ and __NAV__)."""
    page('reel.html', 'pages/reel.html', DATA=json.dumps({'shots': index()}, separators=(',', ':')).replace('</', '<\\/'))


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT / 'tools'))
    import os; os.chdir(ROOT)
    import build_pages
    build(build_pages.page)
