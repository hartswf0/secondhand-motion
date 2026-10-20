"""Build every HTML page in the repository from its template and data files.

usage: python3 tools/build_pages.py        (run from the repository root)

Pages carry their data inline, so each one opens straight from the file system or GitHub Pages.
Images and videos are referenced by relative path.
"""
import csv, glob, json, os, re
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parent.parent
T = ROOT / 'tools' / 'templates'
BATCH = 'batches/2026-10-20-selected-drawings'
DATE = '20 Oct 2026'
HEAD = (T / 'head.html').read_text()

NAV = [('index.html', 'Index'), ('pages/pipeline.html', 'Pipeline'), ('pages/agent-prompt.html', 'Agent prompt'),
       ('pages/archive-doodle-index.html', 'Dataset'), ('pages/giraffe-walks-past.html', 'Giraffe shot'),
       ('pages/traced-keys.html', 'Traced keys'), (f'{BATCH}/index.html', 'Selected drawings')]


def nav(here):
    up = '../' * here.count('/')
    cur = ' aria-current="page"'
    links = ''.join(f'<a href="{up}{p}"{cur if p == here else ""}>{t}</a>' for p, t in NAV)
    return ('<style>.repo-nav{max-width:1080px;margin:0 auto;padding:14px 0 0;display:flex;gap:14px;flex-wrap:wrap;'
            'font:600 13px "Atkinson Hyperlegible","Segoe UI",sans-serif}.repo-nav a{color:#5D6573;text-decoration:none}'
            '.repo-nav a[aria-current]{color:inherit}</style>'
            f'<nav class="repo-nav" aria-label="Repository">{links}</nav>')


def js(d):
    return json.dumps(d, separators=(',', ':')).replace('</', '<\\/')


def write(rel, html):
    p = ROOT / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(html)
    print(f'{rel:42s} {len(html.encode()) / 1e6:6.2f} MB')


def legacy(template, data_text, rel):
    """Pages first built as claude.ai artifacts: add a document head and the repository nav."""
    html = template.replace('__DATA__', data_text)
    head = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')
    html = head + html
    i = html.index('</style>') + len('</style>')
    html = html[:i] + '\n' + nav(rel) + html[i:]
    if 'body{' in html and 'margin:0' not in html.split('body{', 1)[1].split('}', 1)[0]:
        html = html.replace('body{', 'body{margin:0;', 1)
    write(rel, html)


def page(template, rel, **kw):
    html = (T / template).read_text().replace('__HEAD__', HEAD).replace('__NAV__', nav(rel))
    for k, v in kw.items(): html = html.replace(f'__{k}__', v)
    left = set(re.findall(r'__[A-Z_]+__', html))
    assert not left, f'{rel}: unfilled {left}'
    write(rel, html)


def md_page(src, rel, title, tools=''):
    raw = (ROOT / src).read_text()
    body = markdown.markdown(raw, extensions=['tables', 'fenced_code'])
    up = '../' * rel.count('/')
    body = re.sub(r'<code>((?:pages|shots|tools|batches|data|dataset|traced)/[^<\s]+)</code>',
                  lambda m: f'<a href="{up}{m.group(1)}"><code>{m.group(1)}</code></a>' if (ROOT / m.group(1)).exists() else m.group(0), body)
    page('doc.html', rel, TITLE=title, TOOLS=tools, BODY=body, RAW=raw.replace('</', '<\\/'))


def main():
    os.chdir(ROOT)
    tm = lambda n: (T / n).read_text()
    # 1-3: pages from the first sessions
    legacy(tm('dataset_template.html'), (T / 'dataset_compact.json').read_text().replace('</', '<\\/'), 'pages/archive-doodle-index.html')
    legacy(tm('stones_template.html'), (T / 'stones_data.json').read_text().replace('</', '<\\/'), 'pages/doodle-to-footage.html')
    legacy(tm('cartoon_template.html'), (T / 'cartoon_data.json').read_text().replace('</', '<\\/'), 'pages/cartoon-archive.html')
    # 4: the full shot
    shot = ROOT / 'shots/giraffe-walks-past'
    legacy((shot / 'shot_template.html').read_text(), (shot / 'shot.json').read_text().replace('</', '<\\/'), 'pages/giraffe-walks-past.html')
    # 5: traced keys
    tr = json.load(open('traced/traced_keys.json'))
    val = json.load(open(f'{BATCH}/validation.json'))
    rev = {s['category']: s['selected_revision'] for s in val['subjects']}
    for n, e in tr.items():
        e['revision'] = rev.get(n, '?')
        e['reviews'] = len(glob.glob(f'{BATCH}/reviews/{n}-v*.json'))
    page('traced.html', 'pages/traced-keys.html', DATA=js({'batch': '../' + BATCH, 'subjects': tr, 'when': DATE}))
    # 6-7: pipeline and agent prompt
    md_page('PIPELINE.md', 'pages/pipeline.html', 'Pipeline')
    md_page('AGENTS.md', 'pages/agent-prompt.html', 'Agent Prompt',
            tools='<div class="tools"><span class="meta">Source: AGENTS.md. Fill {CATEGORY} and {WAVE} from data/subject_queue.json.</span>'
                  '<button id="copy" type="button">Copy prompt as Markdown</button></div>')
    # index
    recall = min(k['recall'] for e in tr.values() for k in e['keys'])
    still = {n: sum(k['n_strokes'] - k['char_strokes'] for k in e['keys']) / sum(k['n_strokes'] for k in e['keys']) for n, e in tr.items()}
    stages = ['Select', 'Observe', 'Identity', 'Plan', 'Keys', 'Trace', 'Rig', 'In-between', 'Planes', 'Tests', 'Critic']
    board = [{'subject': 'giraffe (full shot)', 'cells': ['done', 'done', 'done', 'done', 'part', 'done', 'done', 'done', 'done', 'part', 'part']}]
    for n, e in tr.items():
        t1 = all(k['recall'] >= 0.98 and k['parts_kept'] >= 1 for k in e['keys'])
        keys = 'done' if still[n] >= 0.9 else 'part'   # stills accepted by critics; B1 held background decides
        board.append({'subject': n + (' (keys)' if n == 'giraffe' else ''), 'cells': ['done', '', 'done', 'done', keys, 'done' if t1 else 'fail', '', '', '', '', '']})
    q = json.load(open('data/subject_queue.json'))['queue']
    works = [
        {'step': '1 · dataset', 'title': 'Archive Doodle Index', 'url': 'pages/archive-doodle-index.html', 'img': 'assets/index.jpg', 'alt': 'Grid of category tiles with match scores',
         'proved': "Every Quick, Draw! category has real archive footage behind it, found by the archive's own image search.", 'num': '16,042', 'numlabel': 'shot matches across 345 categories'},
        {'step': '2 · joint space', 'title': 'Doodle to Footage', 'url': 'pages/doodle-to-footage.html', 'img': 'assets/stones.jpg', 'alt': 'Doodles beside the archive shots they match',
         'proved': "Drawings and footage share one CLIP space once each modality's average is removed.", 'num': '52% → 87%', 'numlabel': 'drawings matched to their own category'},
        {'step': '3 · segment and trace', 'title': 'Cartoon Archive', 'url': 'pages/cartoon-archive.html', 'img': 'assets/traced.jpg', 'alt': 'Line cartoons traced from segmented footage',
         'proved': 'SAM finds the subject in nearly every frame, but outlines traced from masks do not look drawn.', 'num': '0.93', 'numlabel': 'giraffe recognition, drawn keys'},
        {'step': '4 · full shot', 'title': 'Giraffe Walks Past', 'url': 'pages/giraffe-walks-past.html', 'img': 'assets/shot.jpg', 'alt': 'Multiplane doodle cartoon of a giraffe',
         'proved': 'One shot rebuilt as a multiplane cartoon: rotoscoped keys, six depth planes, real camera pan, three blind reviews.',
         'num': f"{sum(1 for t in json.load(open(shot / 'tests.json')) if t['ok'])} / {len(json.load(open(shot / 'tests.json')))}", 'numlabel': 'tests passing'},
        {'step': '5 · look lane', 'title': 'Selected Drawings', 'url': f'{BATCH}/index.html', 'img': f'{BATCH}/selected-drawings-atlas.png', 'alt': 'Atlas of ten selected drawings',
         'proved': 'An image model holds a doodle identity across four keys when a fresh critic names one gap per round.', 'num': '40 keys', 'numlabel': '10 subjects, 19 review rounds'},
        {'step': '6 · the join', 'title': 'Traced Keys', 'url': 'pages/traced-keys.html', 'img': 'assets/traced_grid.png', 'alt': 'Traced strokes of six drawings',
         'proved': 'Raster keys become pen strokes without losing a mark; the traces expose that backgrounds are redrawn per key.',
         'num': f'{recall:.3f}', 'numlabel': 'lowest recall over 40 keys'},
    ]
    page('hub.html', 'index.html', DATE=DATE, TRACE_RECALL=f'≥ {recall:.2f}', TREE=tree(),
         DATA=js({'works': works, 'stages': stages, 'board': board, 'queue': [x for x in q if x.get('wave') == 2],
                  'tests': json.load(open(shot / 'tests.json'))}))


def tree():
    rows = [('index.html', 'this page'), ('PIPELINE.md', 'stages, contracts, tests  → pages/pipeline.html'),
            ('AGENTS.md', 'prompt for an agent taking one subject  → pages/agent-prompt.html'),
            ('pages/', 'every other page, built by tools/build_pages.py'),
            ('dataset/', '345 categories × archive shots: clips.csv, clips.jsonl, categories.csv'),
            ('data/subject_queue.json', 'moving subjects ranked by archive match; wave 2 marked'),
            ('data/quickdraw/fetch.sh', 'fetches the exact Quick, Draw! slices the scripts read'),
            ('shots/giraffe-walks-past/', 'full shot: rig, reward, in-between, planes, tests, critic stills'),
            (f'{BATCH}/', 'look lane: 40 keys, prompts, reviews, repair ledger'),
            ('traced/traced_keys.json', 'the 40 keys as strokes, with layer split and scores'),
            ('tools/', 'trace_keys.py, build_pages.py, page templates')]
    out = []
    for p, d in rows:
        name = f'<a href="{p}">{p}</a>' if (ROOT / p).exists() else p
        out.append(f'{name}{" " * max(2, 44 - len(p))}{d}')
    return '\n'.join(out)


if __name__ == '__main__':
    main()
