"""Build every HTML page in the repository from its template and data files.

usage: python3 tools/build_pages.py        (run from the repository root)

Pages carry their data inline, so each one opens straight from the file system or GitHub Pages.
Images and videos are referenced by relative path.
"""
import csv, glob, json, os, re, sys
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parent.parent
T = ROOT / 'tools' / 'templates'
BATCH = 'batches/2026-10-20-selected-drawings'
DATE = '20 Oct 2026'
HEAD = (T / 'head.html').read_text()

NAV = [('index.html', 'Rack'), ('pages/pipeline.html', 'Pipeline'), ('pages/tests.html', 'Tests'),
       ('pages/agent-prompt.html', 'Agent prompt'), ('pages/archive-doodle-index.html', 'Dataset')]
sys.path.insert(0, str(ROOT / 'tools'))
import brand


def icons(here):
    up = '../' * here.count('/')
    return (f'<link rel="icon" href="{up}favicon.svg" type="image/svg+xml"><link rel="icon" href="{up}favicon-32.png" sizes="32x32">'
            f'<link rel="apple-touch-icon" href="{up}apple-touch-icon.png"><meta name="theme-color" content="#EF9F3A">'
            f'<meta property="og:image" content="{up}assets/brand/social-card.png"><meta property="og:title" content="Secondhand Motion">'
            '<meta property="og:description" content="Archive film, redrawn as moving Quick, Draw! doodles.">')


def nav(here):
    """Site header shared by every page, styled on its own so older pages carry it unchanged."""
    up = '../' * here.count('/')
    cur = ' aria-current="page"'
    links = ''.join(f'<a href="{up}{p}"{cur if p == here else ""}>{t}</a>' for p, t in NAV)
    logo = brand.mark(0, ink='currentColor', sw=3.8, size=34)
    return ('<style>.sm-head{max-width:1200px;margin:0 auto;padding:14px 0 12px;display:flex;align-items:center;gap:10px 22px;flex-wrap:wrap;'
            'border-bottom:2px solid currentColor;color:#161412}'
            '.sm-head .brand{display:flex;align-items:center;gap:8px;text-decoration:none;color:inherit;font:800 20px/1 "Bricolage Grotesque","Helvetica Neue",Arial,sans-serif;letter-spacing:-.01em;margin-right:auto}'
            '.sm-head .brand svg{display:block;flex:none}'
            '.sm-head nav{display:flex;gap:4px 16px;flex-wrap:wrap;font:600 14px "Atkinson Hyperlegible","Segoe UI",sans-serif}'
            '.sm-head nav a{color:inherit;opacity:.72;text-decoration:none;padding:4px 0;border-bottom:2px solid transparent}'
            '.sm-head nav a:hover{opacity:1}.sm-head nav a[aria-current]{opacity:1;border-bottom-color:#EF9F3A}'
            '@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) .sm-head{color:#F1EADD}}'
            ':root[data-theme="dark"] .sm-head{color:#F1EADD}</style>'
            f'<header class="sm-head"><a class="brand" href="{up}index.html" aria-label="Secondhand Motion, the rack">{logo}<span>Secondhand Motion</span></a>'
            f'<nav aria-label="Site">{links}</nav></header>')


def js(d):
    return json.dumps(d, separators=(',', ':')).replace('</', '<\\/')


def write(rel, html):
    p = ROOT / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(html)
    print(f'{rel:42s} {len(html.encode()) / 1e6:6.2f} MB')


def legacy(template, data_text, rel):
    """Pages first built as claude.ai artifacts: add a document head and the repository nav."""
    html = template.replace('__DATA__', data_text)
    head = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' + icons(rel) + '\n')
    html = head + html
    i = html.index('</style>') + len('</style>')
    html = html[:i] + '\n' + nav(rel) + html[i:]
    if 'body{' in html and 'margin:0' not in html.split('body{', 1)[1].split('}', 1)[0]:
        html = html.replace('body{', 'body{margin:0;', 1)
    write(rel, html)


def page(template, rel, **kw):
    html = (T / template).read_text().replace('__HEAD__', HEAD.replace('__ICONS__', icons(rel))).replace('__NAV__', nav(rel))
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
    # catalog: every lot's item.json plus its test results
    import validate
    errs, _ = validate.check(prebuild=True)
    if errs:
        for e in errs: print('ERROR', e)
        raise SystemExit('fix the lots above, then rebuild')
    reg = json.load(open('tests/registry.json'))
    lots = catalog(reg)
    (ROOT / 'data/catalog.json').write_text(json.dumps(lots, indent=1))
    page('tests.html', 'pages/tests.html', DATA=js({'tests': reg['tests'], 'stages': reg['stages'],
         'lots': [{'lot': l['lot'], 'title': l['title'], 'href': '../' + l['href'] if not l['href'].startswith('http') else l['href'],
                   'status': l['status'], 'r': l['r']} for l in lots if l['r']]}))
    mark = brand.mark(0, ink='currentColor', sw=2.6, size=64).replace('width="64" height="64"', 'aria-hidden="true"')
    page('hub.html', 'index.html', DATE=DATE, TREE=tree(),
         DATA=js({'lots': [{k: v for k, v in l.items() if k != 'r'} for l in lots], 'stages': reg['stages'], 'brand': brand.data(), 'mark': mark,
                  'n_active': sum(t['status'] == 'active' for t in reg['tests']), 'n_planned': sum(t['status'] == 'planned' for t in reg['tests'])}))


def catalog(reg):
    from new_subject import lot_files
    active = [t['id'] for t in reg['tests'] if t['status'] == 'active']
    out = []
    for p in lot_files():
        it = json.load(open(p))
        r = {}
        if it.get('tests'):
            tf = ROOT / it['tests']
            rows = json.load(open(tf))
            extra = tf.with_name('tests-extra.json')
            if extra.exists(): rows += json.load(open(extra))
            for t in rows: r[t['id']] = {'value': t.get('value'), 'unit': t.get('unit', ''), 'ok': t.get('ok')}
        kind = 'queued' if it.get('status') == 'queued' else 'shot' if it.get('kind') == 'shot' else 'keys'
        applies = {t['id'] for t in reg['tests'] if kind in t.get('applies', [])}
        r = {i: v for i, v in r.items() if i in applies}
        ran = [i for i in active if i in applies] if it.get('tests') else []
        it['t'] = {'pass': sum(r.get(i, {}).get('ok') is True for i in ran), 'fail': sum(r.get(i, {}).get('ok') is False for i in ran), 'total': len(ran)}
        if it.get('tests'):
            for i in ran: r.setdefault(i, {'value': 'not run', 'unit': '', 'ok': None})
        it['r'] = r
        it['href'] = it['links'][0]['href'] if it.get('links') else p.parent.relative_to(ROOT).as_posix() + '/'
        it.setdefault('stage', None)
        out.append(it)
    out.sort(key=lambda x: x['lot'])
    return out


def tree():
    rows = [('index.html', 'the rack, built from every item.json'),
            ('shots/<lot>/', 'one folder per subject or shot: item.json, tests.json, work'),
            ('data/lots/', 'lots that are pages or studies'),
            ('tests/registry.json', 'every test: id, bar, how, stage, active or planned'),
            ('data/catalog.json', 'all lots and results, generated'),
            ('batches/', 'raw look-lane batches as delivered'),
            ('pages/', 'built pages'),
            ('tools/', 'new_subject, import_batch, validate, trace_keys, build_pages, brand'),
            ('AGENTS.md', 'prompt for an agent taking one lot'),
            ('PIPELINE.md', 'the thirteen stages')]
    out = []
    for p, d in rows:
        name = f'<a href="{p}">{p}</a>' if (ROOT / p).exists() else p
        out.append(f'{name}{" " * max(2, 22 - len(p))}{d}')
    return '\n'.join(out)


if __name__ == '__main__':
    main()
