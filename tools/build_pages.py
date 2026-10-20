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

NAV = [('index.html', 'Rack'), ('pages/projector.html', 'Projector'), ('production/index.html', 'Production'), ('pages/pipeline.html', 'Pipeline'), ('pages/line.html', 'Line'),
       ('pages/tests.html', 'Tests'), ('pages/agent-prompt.html', 'Agent prompt'), ('pages/archive-doodle-index.html', 'Dataset')]
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
    body = re.sub(r'<code>((?:pages|shots|tools|batches|data|dataset|traced|production|docs)/[^<\s]+)</code>',
                  lambda m: f'<a href="{up}{m.group(1)}"><code>{m.group(1)}</code></a>' if (ROOT / m.group(1)).exists() else m.group(0), body)
    page('doc.html', rel, TITLE=title, TOOLS=tools, BODY=body, RAW=raw.replace('</', '<\\/'))


def main():
    os.chdir(ROOT)
    tm = lambda n: (T / n).read_text()
    # Rebuild the production workbench with embedded data for offline use.
    import runpy
    runpy.run_path(str(ROOT / 'production/tools/build_viewer.py'), run_name='__main__')
    # 1-3: pages from the first sessions
    legacy(tm('dataset_template.html'), (T / 'dataset_compact.json').read_text().replace('</', '<\\/'), 'pages/archive-doodle-index.html')
    legacy(tm('stones_template.html'), (T / 'stones_data.json').read_text().replace('</', '<\\/'), 'pages/doodle-to-footage.html')
    legacy(tm('cartoon_template.html'), (T / 'cartoon_data.json').read_text().replace('</', '<\\/'), 'pages/cartoon-archive.html')
    # 4: the full shot
    shot = ROOT / 'shots/giraffe-walks-past'
    legacy((shot / 'shot_template.html').read_text(), (shot / 'shot.json').read_text().replace('</', '<\\/'), 'pages/giraffe-walks-past.html')
    # 5: traced keys now play in the projector; the old address forwards there
    write('pages/traced-keys.html', '<!doctype html><html lang="en"><meta charset="utf-8"><title>Traced Keys</title>'
          '<meta http-equiv="refresh" content="0; url=projector.html#dog"><link rel="icon" href="../favicon.svg">'
          '<script>location.replace("projector.html"+(location.hash||"#dog"))</script><a href="projector.html">Traced keys are in the projector</a>')
    # 6-7: pipeline and agent prompt
    md_page('PIPELINE.md', 'pages/pipeline.html', 'Pipeline')
    if (ROOT / 'docs/production-line.md').exists(): md_page('docs/production-line.md', 'pages/line.html', 'Production Line')
    md_page('docs/giraffe-walks-past.md', 'pages/how-giraffe-walks-past-was-made.html', 'How Giraffe Walks Past Was Made')
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
    projector(lots, reg)
    shot_pages()
    mark = brand.mark(0, ink='currentColor', sw=2.6, size=64).replace('width="64" height="64"', 'aria-hidden="true"')
    page('hub.html', 'index.html', DATE=DATE, TREE=tree(),
         DATA=js({'lots': [{k: v for k, v in l.items() if k != 'r'} for l in lots], 'stages': reg['stages'], 'brand': brand.data(), 'mark': mark,
                  'n_active': sum(t['status'] == 'active' for t in reg['tests']), 'n_planned': sum(t['status'] == 'planned' for t in reg['tests'])}))

    __import__('build_wave2_pages').build(ROOT, HEAD, nav, icons, write)


def shot_pages():
    """A full shot page (cartoon, over footage, footage, planes in depth, silhouettes) for every SAM shot."""
    T = (T_DIR := ROOT / 'tools' / 'templates' / 'shot_page.html').read_text() if (ROOT / 'tools/templates/shot_page.html').exists() else None
    if not T: return
    for f in sorted(list(ROOT.glob('shots/*-sam/shot.json')) + list(ROOT.glob('shots/*-gwp/shot.json'))):
        sid = f.parent.name; S = json.load(open(f))
        S['footage'] = [f'../shots/{sid}/{u}' for u in S['footage']]
        rv = f.parent / 'reviews'
        rounds = ''.join(f'<div class="plane" style="flex-direction:column;align-items:flex-start"><b>Round {i + 1} · {v.get("identity_verdict", "")}</b>'
                         f'<span class="meta" style="margin:0;white-space:normal">Named “{v.get("named_subject", "")}”; motion {v.get("motion_reads", "")}. {v.get("identity_gap", "")}</span></div>'
                         for i, v in enumerate(json.load(open(p)) for p in sorted(rv.glob('critic-*.json')))) if rv.exists() else ''
        reg = S.get('registration', [])
        lede = (f"{S['category'].capitalize()} from the archive, redrawn the way Giraffe Walks Past was made, starting from drawn poses. "
                f"SAM 2.1 traced the {S['category']} in every frame. The four keys an image model drew in the chosen doodle's identity, each approved by a "
                f"critic, were traced to strokes, split from their scenery by the silhouette and moved onto it; in-betweens match strokes key to key and follow "
                f"the silhouette frame by frame. The scenery is drawn once, and the silhouette is painted as a cel under the character.")
        if sid.endswith('-gwp'):
            nk = len(S['cast']['keys'])
            lede = (f"{S['category'].capitalize()} from the archive, made the way Giraffe Walks Past was made. SAM 2.1 traced the {S['category']} in every frame. "
                    f"The rig is the chosen Quick, Draw! doodle itself ({S['cast']['source'].split(' as ')[0]}): its own lines, bent at a few joints, so every frame "
                    f"is the same drawing. {nk} keys were placed by eye over the silhouettes; in-betweens follow the silhouette frame by frame. "
                    f"Scenery is real Quick, Draw! doodles on depth planes that slide with the measured camera; the silhouette is painted as a cel.")
        html = T.replace('__TITLE__', S['title']).replace('__LEDE__', lede).replace('__ROUNDS__', rounds or '<p class="meta">No review yet.</p>')
        html = html.replace('__DATA__', json.dumps(S, separators=(',', ':')).replace('</', '<\\/'))
        head = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                + icons(f'pages/{sid}.html') + '\n')
        html = head + html; i = html.index('</style>') + len('</style>'); html = html[:i] + '\n' + nav(f'pages/{sid}.html') + html[i:]
        write(f'pages/{sid}.html', html)


def projector(lots, reg):
    def pack(shot, base, method):
        return {'W': shot['W'], 'H': shot['H'], 'fps': shot['fps'], 'z_ref': shot['z_ref'], 'planes': shot['planes'], 'camera': shot['camera'],
                'objects': shot['objects'], 'cast': shot['cast']['frames'], 'keys': shot['cast']['keys'], 'N': len(shot['cast']['frames']),
                'footage': [u if u.startswith('data:') else base + u for u in shot['footage']], 'masks': shot['masks'],
                'notes': {x['f']: x['note'] for x in shot['xsheet'] if x['note']}, 'method': method}
    shots = {'giraffe-walks-past': pack(json.load(open('shots/giraffe-walks-past/shot.json')), '',
             'Motion lane, rig drawn by the agent. Nine keys drawn over SAM silhouettes, in-betweened with planted feet and the measured camera pan; six depth planes.')}
    M = json.load(open('traced/matches.json'))
    by = {l['id']: l for l in lots}
    L = [{'id': 'giraffe-walks-past', 'lot': by['giraffe-walks-past']['lot'], 'title': 'Giraffe Walks Past', 'lane': 'motion', 'kind': 'shot'}]
    for cat in sorted(M):
        sid = f'{cat}-redraw'
        if sid in by:
            sh = json.load(open(f'shots/{sid}/shot.json')); rig = json.load(open(f'shots/{sid}/rig.json'))
            shots[sid] = pack(sh, f'../shots/{sid}/', f"Puppet redraw. The chosen Quick, Draw! {cat} (key_id {sh['design']['key_id']}, all {sh['design']['strokes']} strokes) moved by "
                              f"{len(rig['bones'])} bones the agent placed on {len(sh['cast']['keys'])} key frames by eye; background drawn once from the look-lane key.")
            L.append({'id': sid, 'lot': by[sid]['lot'], 'title': cat.capitalize(), 'lane': 'motion', 'kind': 'shot'})
        sid3 = f'{cat}-gwp'
        if sid3 in by:
            sh = json.load(open(f'shots/{sid3}/shot.json'))
            shots[sid3] = pack(sh, f'../shots/{sid3}/', f"The Giraffe Walks Past way. SAM on every frame; the rig is the chosen Quick, Draw! doodle itself ({sh['cast']['source'].split(' as ')[0]}), bent at a few joints, so every frame is the same drawing; {len(sh['cast']['keys'])} keys placed by eye over the silhouettes; Quick, Draw! scenery on planes sliding with the measured camera; cel from the silhouette.")
            L.append({'id': sid3, 'lot': by[sid3]['lot'], 'title': cat.capitalize(), 'lane': 'gwp', 'kind': 'shot'})
        sid2 = f'{cat}-sam'
        if sid2 in by:
            sh = json.load(open(f'shots/{sid2}/shot.json'))
            shots[sid2] = pack(sh, f'../shots/{sid2}/', 'Drawn keys over SAM. SAM 2.1 masked the subject in every frame; the four critic-approved drawn keys were split from their scenery by the mask and moved onto it; in-betweens match strokes and follow each frame\'s silhouette; scenery drawn once; the silhouette is painted as a cel.')
            L.append({'id': sid2, 'lot': by[sid2]['lot'], 'title': cat.capitalize(), 'lane': 'join', 'kind': 'shot'})
    for gp in sorted(Path('shots').glob('*-gwp/shot.json')):
        sid3 = gp.parent.name; cat = sid3[:-4]
        if cat in M or sid3 not in by: continue
        sh = json.load(open(gp))
        shots[sid3] = pack(sh, f'../shots/{sid3}/', f"The Giraffe Walks Past way, wave 2. Frames, SAM 2.1 masks and Depth Anything depth computed on GitHub's machines; the rig is the chosen Quick, Draw! doodle itself ({sh['cast']['source'].split(';')[0]}); keys posed toward the six generated keys and placed on the silhouettes; scenery planes set from measured depth.")
        L.append({'id': sid3, 'lot': by[sid3]['lot'], 'title': cat.replace('-', ' ').capitalize(), 'lane': 'gwp', 'kind': 'shot'})

    thumbs = {}
    for cat in sorted(M):
        pv = json.load(open(f'{BATCH}/subjects/{cat}/preview-data.json')); t0 = pv['interval'][0]
        thumbs[cat] = pv['source_frames']
        M[cat]['key_times'] = [round(t - t0, 3) for t in M[cat]['key_times']]          # excerpt time starts at the interval start
        L.append({'id': cat, 'lot': by[cat]['lot'], 'title': cat.capitalize(), 'lane': 'look', 'kind': 'traced', 'duration': M[cat]['duration'],
                  'thumb_times': [round(t - t0, 3) for t in pv['source_frame_times']],
                  'video': f'../{BATCH}/subjects/{cat}/source-excerpt.mp4', 'base': f'../{BATCH}/subjects/{cat}/'})
    C = json.load(open('data/lane_compare.json'))
    m, g = C['rows'][0]['z'], C['rows'][1]['z']
    C['why'] = (f"Measured against real doodles, each lane fails where the other passes. The motion lane draws about as many strokes as a "
                f"real giraffe doodle ({m[0]:+.1f} standard deviations) but its lines turn too often and run too long between points "
                f"(turning {m[4]:+.1f}, segment length {m[2]:+.1f}): the rig's wobble reads as machine jitter. The look lane draws lines that "
                f"turn like a person's ({g[4]:+.1f}) but far too many of them ({g[0]:+.1f} for the giraffe; real ones median "
                f"{int(C['median_strokes']['giraffe'])} strokes). The join to build next keeps the look lane's line and the motion lane's "
                f"stroke budget: trace the drawn key, fit the rig to it, and redraw each rig part as one traced stroke. Until then, the "
                f"projector shows both honestly: the look lane now moves, but its in-betweens slide and swap because nothing holds the body together.")
    cat_by = {l['lot']: l for l in lots}
    res = []
    for cat in sorted(M):
        look = by[cat]['r']; pup = by.get(f'{cat}-redraw', {}).get('r', {})
        cell = lambda r, i: {'v': r[i]['value'], 'ok': r[i]['ok']} if i in r else None
        res.append({'cat': cat, 'look': {i: cell(look, i) for i in ('M2', 'T3', 'B1', 'J4')},
                    'pup': {i: cell(pup, i) for i in ('M1', 'M2', 'T3', 'B1', 'J4', 'J1', 'M3', 'M5')},
                    'sam': {i: cell(by.get(f'{cat}-sam', {}).get('r', {}), i) for i in ('M1', 'M2', 'T3', 'B1', 'J4', 'J1', 'M3')}})
    page('projector.html', 'pages/projector.html', DATA=js({'lots': L, 'shots': shots, 'traced': M, 'results': res, 'compare': C, 'registry': reg['tests'], 'thumbs': thumbs,
         'catalog': {l['lot']: {'r': l['r']} for l in lots}}))


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
        it['gait'] = brand.GAIT_NAMES[(int(it['lot'].split('-')[1]) - 1) % len(brand.GAIT_NAMES)]
        out.append(it)
    out.sort(key=lambda x: x['lot'])
    return out


def tree():
    rows = [('index.html', 'the rack, built from every item.json'),
            ('shots/<lot>/', 'one folder per subject or shot: item.json, tests.json, work'),
            ('data/lots/', 'lots that are pages or studies'),
            ('production/', '100-clip pool, timed key references and local worker queue'),
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
