"""Record a critic verdict for a subject and give its shot a lot on the rack.
usage: python3 tools/finish_subject.py <slug> <verdict.json> <packet-id> [round]"""
import json, os, sys
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT / 'tools'))
from new_subject import next_lot
slug, vp, packet = sys.argv[1:4]; rnd = int(sys.argv[4]) if len(sys.argv) > 4 else 1
d = ROOT / 'shots' / f'{slug}-gwp'; (d / 'reviews').mkdir(exist_ok=True)
v = json.load(open(vp)); v.update(_packet=packet, _round=rnd); json.dump(v, open(d / 'reviews' / f'critic-{rnd}.json', 'w'), indent=1)
S = json.load(open(d / 'shot.json')); Image.open(d / 'critic' / 'keys.png').crop((0, 0, S['W'], S['H'])).save(d / 'cover.png')
w4 = [x['slug'] for x in json.load(open(ROOT / 'data' / 'wave4.json'))['subjects']] if (ROOT / 'data' / 'wave4.json').exists() else []
w5 = [x['slug'] for x in json.load(open(ROOT / 'data' / 'wave5.json'))['subjects']] if (ROOT / 'data' / 'wave5.json').exists() else []
wave = 5 if slug in w5 else 4 if slug in w4 else 3 if (ROOT / 'shots' / slug / 'plan.json').exists() else 2 if (ROOT / 'shots' / slug / 'keyplan.json').exists() else 1
if not (d / 'item.json').exists():
    json.dump({'lot': next_lot(), 'id': f'{slug}-gwp', 'kind': 'shot', 'title': f"{slug.replace('-', ' ').capitalize()}, the Giraffe Walks Past Way", 'category': slug, 'wave': wave,
               'lane': 'join', 'stage': 10, 'status': 'in progress', 'added': '2026-10-20',
               'blurb': 'Survey, frames, SAM 2.1 masks and depth on GitHub; the chosen doodle itself as the rig, keyed by eye on the silhouettes; Quick, Draw! scenery on planes set from measured depth.',
               'cover': f'shots/{slug}-gwp/cover.png', 'cover_alt': f"shots/{slug}-gwp/frames/f{S['cast']['keys'][len(S['cast']['keys']) // 2]:03d}.jpg",
               'links': [{'label': 'Shot page', 'href': f'pages/{slug}-gwp.html'}, {'label': 'Open in the projector', 'href': f'pages/projector.html#{slug}-gwp'},
                         {'label': 'Rig spec', 'href': f"rigs/{slug.replace('-', '_')}_spec.json"}] + ([{'label': 'Survey', 'href': f'shots/{slug}/survey/sheet.jpg'}] if wave >= 3 else []),
               'tests': f'shots/{slug}-gwp/tests.json', 'tags': ['SAM', 'depth', 'doodle rig', f'wave {wave}']}, open(d / 'item.json', 'w'), indent=1)
os.system(f'{sys.executable} {ROOT}/tools/gwp_tests.py {slug} > /dev/null')
print(slug, v['identity_verdict'], v['motion_reads'], v.get('follows_film'))
