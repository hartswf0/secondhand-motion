"""Step 2 for a wave-4 subject: write shots/<slug>/plan.json, source.json, design.json and design.png from the
choices made by looking at shots/<slug>/survey/sheet.jpg and doodles.jpg.

usage: python3 tools/plan_subject.py <slug> --interval A B --label "a lion." --doodle N --why "..." [--step 0.5]
       python3 tools/plan_subject.py <slug> --reject "why the clip cannot be used"
Key times run from A to B every --step seconds (B included). --doodle is the number printed on doodles.jpg (counted from 1).
"""
import argparse, json, sys
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('slug'); ap.add_argument('--interval', nargs=2, type=float); ap.add_argument('--label')
    ap.add_argument('--doodle', type=int); ap.add_argument('--why', default=''); ap.add_argument('--step', type=float, default=0.5); ap.add_argument('--reject')
    a = ap.parse_args()
    W = json.load(open(ROOT / 'data' / 'wave4.json')); S = next(s for s in W['subjects'] if s['slug'] == a.slug); d = ROOT / 'shots' / a.slug
    if a.reject:
        (d / 'rejected.txt').write_text(a.reject + '\n'); print(a.slug, 'rejected'); return
    A, B = a.interval; n = int(round((B - A) / a.step))
    if abs(A + n * a.step - B) > 1e-6: sys.exit(f'interval {A}-{B} is not a whole number of {a.step} s steps')
    times = [round(A + i * a.step, 3) for i in range(n + 1)]
    bank = json.load(open(d / 'survey' / 'doodles.json')); dr = bank['drawings'][a.doodle - 1]   # the sheet numbers its doodles from 1
    plan = {'slug': a.slug, 'category': S['category'], 'video_url': S['video_url'], 'clip_id': S['clip_id'], 'interval': [A, B], 'key_times': times,
            'label': a.label, 'why': a.why, 'doodle_key_id': dr['key_id'], 'doodle_bank_index': a.doodle - 1, 'doodle_sheet_number': a.doodle}
    json.dump(plan, open(d / 'plan.json', 'w'), indent=1)
    src = {k: S[k] for k in ('clip_id', 'source_id', 'source_title', 'source_year', 'video_url', 'shot_page_url', 'source_page_url', 'original_source_url', 'rights_statement')}
    src.update(start_seconds=A, end_seconds=B, category=S['category'], why_this_clip=a.why, pool='production/data/candidates-100.json')
    json.dump({'source': src}, open(d / 'source.json', 'w'), indent=1)
    design = {'key_id': dr['key_id'], 'word': S['category'], 'recognized': True, 'countrycode': dr['countrycode'], 'drawing': dr['drawing'], 'transform': None,
              'source_url': bank['source_url'], 'credit': bank['credit']}
    json.dump(design, open(d / 'design.json', 'w'))
    im = Image.new('RGB', (280, 280), 'white'); g = ImageDraw.Draw(im)
    for xs, ys in dr['drawing']: g.line([(12 + x, 12 + y) for x, y in zip(xs, ys)], fill='black', width=3)
    im.save(d / 'design.png')
    print(a.slug, len(times), 'keys', times[0], '..', times[-1])


if __name__ == '__main__':
    main()
