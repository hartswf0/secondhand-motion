"""Build static, source-backed Wave 2 draft-key pages. No animation or gate inference."""
from pathlib import Path
from html import escape
import json
import os
from urllib.parse import urlsplit

CSS = '''<style>
.wrap{gap:28px}.breadcrumbs{display:flex;gap:10px 22px;flex-wrap:wrap;font-size:14px}.status{display:inline-block;width:fit-content;padding:5px 10px;border:1px solid var(--rule-strong);border-radius:4px;background:var(--tag-soft);color:var(--tag-ink);font:600 12px var(--mono)}.key-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.key-card,.gallery-card{margin:0;border:1px solid var(--rule);background:var(--sheet);border-radius:8px;overflow:hidden;min-width:0}.key-card img,.gallery-card img{display:block;width:100%;aspect-ratio:4/3;object-fit:contain;background:#fff}.key-card figcaption{padding:12px 14px}.key-head{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;margin-bottom:6px;font:600 12px var(--mono)}.key-card p{margin:0;font-size:15px}.key-card a{display:block}.key-comparison{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));background:#fff}.key-comparison>div{min-width:0}.key-comparison>div+div{border-left:1px solid var(--rule)}.comparison-label{display:block;padding:7px 9px;background:var(--sheet);color:var(--muted);font:600 10px/1.4 var(--mono);letter-spacing:.04em;text-transform:uppercase}.key-comparison.single{grid-template-columns:1fr}.artifact-links{display:flex;flex-wrap:wrap;gap:10px 22px;font-size:14px}.plate{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:24px;align-items:center}.plate figure{margin:0}.plate img{width:100%;display:block;max-height:390px;object-fit:contain;background:#fff;border:1px solid var(--rule);border-radius:8px}.plate figcaption{font-size:13px;color:var(--muted);margin-top:6px}details{border:1px solid var(--rule);background:var(--sheet);border-radius:8px;padding:16px;min-width:0}summary{cursor:pointer;font:700 18px var(--display)}.detail-body{padding-top:18px;display:flex;flex-direction:column;gap:18px}.detail-body p{margin:0}.reference{display:block;width:100%;max-height:680px;object-fit:contain;background:#fff}.design-reference{max-width:520px;max-height:420px}.source-video{display:block;width:100%;max-height:600px;background:#161412}.provenance{display:grid;grid-template-columns:130px minmax(0,1fr);gap:7px 16px;margin:0;font-size:14px}.provenance dt{color:var(--muted)}.provenance dd{margin:0;overflow-wrap:anywhere}.inline-links{display:flex;gap:12px 22px;flex-wrap:wrap}.gallery-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}.gallery-card>a{display:block;color:inherit;text-decoration:none}.gallery-card .card-body{padding:15px;display:flex;flex-direction:column;gap:8px}.gallery-card h2{font-size:24px}.gallery-card p{margin:0;font-size:14px}.gallery-card .status{font-size:10px}.scope{max-width:82ch}.meta,.note,.detail-body,figcaption{overflow-wrap:anywhere}footer{border-top:1px solid var(--rule);padding-top:20px;font-size:13px;color:var(--muted)}@media(max-width:780px){.key-grid,.gallery-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.plate{grid-template-columns:1fr}}@media(max-width:480px){.key-grid,.gallery-grid{grid-template-columns:1fr}.provenance{grid-template-columns:1fr;gap:2px}.provenance dd{margin-bottom:10px}.wrap{gap:24px}.key-card img{max-height:340px}}
</style>'''


def e(value):
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    return escape(str(value if value is not None else ''), quote=True)


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else (default if default is not None else {})


def first_file(folder, candidates):
    for candidate in candidates:
        p = folder / candidate
        if p.is_file():
            return p
    return None


def href(path, page):
    return Path(os.path.relpath(path, page.parent)).as_posix()


def image(path, page, alt, cls='reference'):
    if path is None:
        return '<p class="meta">Asset pending.</p>'
    url = e(href(path, page))
    return f'<a href="{url}"><img class="{cls}" src="{url}" alt="{e(alt)}" loading="lazy"></a>'


def seconds(value):
    try:
        return f'{float(value):.3f}'.rstrip('0').rstrip('.') + ' s'
    except (TypeError, ValueError):
        return 'Time pending'


def interval_label(value):
    if isinstance(value, dict):
        value = [value.get('start', value.get('start_seconds')), value.get('end', value.get('end_seconds'))]
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return f'{seconds(value[0])} – {seconds(value[1])}'
    return 'Interval pending'


def assembled(folder):
    """Only advertise an assembly when its player, timeline and movies exist."""
    base = folder/'integrated'
    needed = ['index.html', 'shot.json', 'cartoon.mp4', 'comparison.mp4', 'poster.png']
    return read(base/'shot.json') if all((base/p).is_file() for p in needed) else {}


def link(url, text):
    if not url:
        return ''
    if urlsplit(str(url)).scheme not in ('', 'http', 'https'):
        return ''
    return f'<a href="{e(url)}">{e(text)}</a>'


def discover(root):
    rows = []
    for folder in sorted((root/'shots').iterdir()):
        if not folder.is_dir():
            continue
        item = read(folder/'item.json')
        if item.get('wave') != 2:
            continue
        required = [folder/'keys/revisions/board-v1.png', folder/'source.json', folder/'keyplan.json']
        required += [folder/'keys'/f'key-{n:02d}.png' for n in range(1,7)]
        if not all(p.is_file() for p in required):
            continue
        rows.append({'folder':folder, 'item':item, 'source':read(folder/'source.json'), 'plan':read(folder/'keyplan.json')})
    rows.sort(key=lambda row: row['item'].get('lot', row['folder'].name))
    return rows


def document(title, body, rel, head, nav, icons):
    return (head.replace('__ICONS__', icons(rel)) + f'<title>{e(title)} · Secondhand Motion</title>' + CSS +
            f'<body><div class="wrap">{nav(rel)}{body}</div></body></html>')


def shot_body(row, root):
    folder, item, raw, plan = row['folder'], row['item'], row['source'], row['plan']
    page = folder/'index.html'
    source = {**(raw.get('source', {}) if isinstance(raw.get('source'),dict) else {}), **raw}
    title = item.get('title', folder.name.replace('-', ' ').title())
    selected = folder/'source-review/selected'
    design = first_file(folder, ['source-review/selected/selected-design.png', 'design.png'])
    design_data = read(selected/'selected-design.json') or read(folder/'design.json')
    sheets = sorted(selected.glob('*-16frames.*'))
    source_sheet = sheets[0] if sheets else first_file(folder, ['contact-sheet.png'])
    background = first_file(folder, ['keys/bg-plate.png','keys/background.png','keys/held-background.png','keys/bg.png'])
    keys = plan.get('keys', [])
    cards = []
    for n in range(1,7):
        key = keys[n-1] if n <= len(keys) and isinstance(keys[n-1],dict) else {}
        time = key.get('time',key.get('source_time',key.get('time_seconds')))
        pose = key.get('pose',key.get('note','Pose note pending.'))
        asset = folder/'keys'/f'key-{n:02d}.png'
        photo = selected/f'source-{n:02d}.jpg'
        drawing = '<div><span class="comparison-label">Draft drawing</span>' + image(asset,page,f'Draft key {n}: {pose}', 'key-image') + '</div>'
        reference = ('<div><span class="comparison-label">Source photograph</span>' + image(photo,page,f'Exact source photograph for key {n} at {seconds(time)}', 'key-image') + '</div>') if photo.is_file() else ''
        pair_class = 'key-comparison' if reference else 'key-comparison single'
        cards.append(f'<figure class="key-card"><div class="{pair_class}">{reference}{drawing}</div><figcaption><div class="key-head"><span>KEY {n:02d}</span><span>{e(seconds(time))}</span></div><p>{e(pose)}</p></figcaption></figure>')
    interval = source.get('interval_seconds', source.get('interval', plan.get('interval_seconds')))
    source_title = source.get('source_title',source.get('title','Source title pending'))
    rights = source.get('rights',source.get('rights_statement','Reported rights not recorded'))
    source_url = source.get('page_url',source.get('shot_page_url',source.get('source_page_url')))
    video_url = source.get('video_url')
    # Prefer a packaged local video. External source video remains opt-in via controls.
    local_video = first_file(folder, ['source.mp4','source-review/selected/source.mp4','source-review/selected/clip.mp4'])
    if local_video:
        video_url = href(local_video,page)
    video_html = (f'<video class="source-video" controls playsinline preload="none" src="{e(video_url)}"></video>' if video_url and urlsplit(str(video_url)).scheme in ('','http','https') else '<p class="meta">Source video URL pending.</p>')
    video_kind = 'Packaged source video.' if local_video else 'Archive video is online; playback starts only when requested.'
    provenance_rows = [('Source',source_title),('Clip ID',source.get('clip_id','Not recorded')),('Source ID',source.get('source_id','Not recorded')),('Selected interval',interval_label(interval)),('Reported rights',rights),('Selection reason',source.get('why_this_clip',source.get('reason',source.get('selection_reason','See source record.'))))]
    provenance = ''.join(f'<dt>{e(k)}</dt><dd>{e(v)}</dd>' for k,v in provenance_rows)
    bg_note = plan.get('background_note',plan.get('background', 'A separate plate is retained for this shot. Holding it has not been measured or approved.'))
    if isinstance(bg_note,dict):
        bg_note = bg_note.get('note',bg_note.get('description', 'A separate plate is retained for this shot.'))
    bg_html = (f'<div class="plate"><figure>{image(background,page,"Separate held-background draft")}<figcaption>Background plate · separate from all six character keys</figcaption></figure><p>{e(bg_note)}</p></div>' if background else '<p class="note">Separate held-background plate pending. Background stability is not yet tested.</p>')
    design_credit = design_data.get('credit','Quick, Draw! contributors / Google Creative Lab; CC BY 4.0')
    revision = str(plan.get('revision', 'v1'))
    current_board = first_file(folder, [f'keys/revisions/board-{revision}.png', 'keys/revisions/board-v2.png', 'keys/revisions/board-v1.png'])
    latest_review = first_file(folder, ['reviews/blind-v3.json', 'reviews/blind-v2.json', 'reviews/blind-v1.json'])
    records = [('keys/traced.json', 'Traced strokes'), ('keys/gates.json', 'Gate record'), ('ledger.jsonl', 'Revision ledger')]
    artifact_links = [link(href(folder/name,page), label) for name,label in records if (folder/name).is_file()]
    if latest_review:
        artifact_links.append(link(href(latest_review,page), 'Independent still review · '+latest_review.stem.removeprefix('blind-')))
    if current_board:
        artifact_links.append(link(href(current_board,page), 'Generation board · '+revision))
    artifact_section = ('<section aria-labelledby="records-heading"><h2 id="records-heading">Current artifact records</h2><p class="meta">Selected key revision '+e(revision)+'. These records describe the work and still review; they do not constitute motion approval.</p><div class="artifact-links">'+''.join(artifact_links)+'</div></section>') if artifact_links else ''
    html = f'''<header class="page"><div class="eyebrow">{e(item.get('lot','Wave 2'))} · Wave 2 / draft keys · {e(revision)}</div><h1>{e(title)}</h1><p class="lede">Six proposed character keys, planned against the selected source interval.</p><span class="status">DRAFT RASTER KEYS · MOTION NOT APPROVED</span></header>
<nav class="breadcrumbs" aria-label="Related pages"><a href="../../index.html">← Rack</a><a href="../wave2-keyframes.html">All Wave 2 keyframes</a></nav>
<div class="note scope"><b>Still drawings, in source order.</b><p>These are draft key proposals. No key animation is presented, and no pipeline gate is claimed passed by this page. Still-key approval and normal-speed playback approval are separate. No training ran.</p></div>
<section aria-labelledby="keys-heading"><h2 id="keys-heading">The six keys</h2><p class="meta">Source clip times · {e(interval_label(interval))}. Open any drawing at full resolution.</p><div class="key-grid">{''.join(cards)}</div></section>
<section aria-labelledby="background-heading"><h2 id="background-heading">Separate held background</h2>{bg_html}</section>
<section aria-label="References and provenance"><details><summary>The real Quick, Draw! design</summary><div class="detail-body">{image(design,page,'Selected real Quick, Draw! design','reference design-reference')}<p class="meta">Key ID: {e(design_data.get('key_id','Not recorded'))}<br>{e(design_credit)}</p><div class="inline-links">{link(href(selected/'selected-design.json',page),'Selected design record') if (selected/'selected-design.json').exists() else ''}{link(design_data.get('source_url'),'Quick, Draw! dataset')}</div></div></details>
<details><summary>The source: 16 timestamped photographs</summary><div class="detail-body"><p class="meta">Reference photographs from the selected interval, rather than authored keys.</p>{image(source_sheet,page,'Sixteen timestamped source photographs')}<p>{e(source_title)} · {e(interval_label(interval))}</p></div></details>
<details><summary>Source video, interval &amp; provenance</summary><div class="detail-body"><p class="meta">{e(video_kind)} The selected interval is {e(interval_label(interval))}, relative to this downloaded archive clip.</p>{video_html}<dl class="provenance">{provenance}</dl><div class="inline-links">{link(source_url,'Archive source page')}{link(video_url,'Open source video')}{link('source.json','Source record')}{link('keyplan.json','Key plan')}{link('keys/revisions/board-v1.png','Original generated board')}</div><details><summary>Full source record</summary><pre>{e(json.dumps(raw,indent=2,ensure_ascii=False))}</pre></details></div></details></section>
{artifact_section}
<footer>Draft raster references. Trace fidelity, recognition, identity, background stability, rigging, contacts, and playback require their own evidence and review. <a href="../../pages/pipeline.html">Pipeline gates</a>.</footer>'''

    timeline = assembled(folder)
    if timeline:
        frames = timeline.get('frame_count', len(timeline.get('frames', [])))
        summary = timeline.get('assembly_summary', 'Source-matched character movement with separate scene layers.')
        note = timeline.get('review_note', '' if 'pending' in summary.lower() else 'Final playback review remains pending.')
        assembly = f'<section><h2>Assembled clip</h2><video class="source-video" controls playsinline preload="metadata" poster="integrated/poster.png" src="integrated/cartoon.mp4"></video><p><a href="integrated/index.html">Open the assembled review copy and synchronized source comparison →</a></p><p class="meta">{e(frames)} rendered frames at {e(timeline.get("fps"))} fps · {e(len(timeline.get("keys", [])))} integrated keys. {e(summary)} {e(note)}</p></section>'
        html = html.replace('<section aria-labelledby="keys-heading">', assembly+'<section aria-labelledby="keys-heading">',1)
        html = html.replace('No key animation is presented, and no pipeline gate is claimed passed by this page.', 'An assembled review copy is now available above. The isolated drafts below are retained as revision evidence.')
    return html


def gallery_body(rows, root):
    ready, drafts = [], []
    page = root/'shots/wave2-keyframes.html'
    for row in rows:
        folder,item,source = row['folder'],row['item'],row['source']
        title=item.get('title',folder.name.replace('-',' ').title())
        time_span=interval_label(source.get('interval_seconds',source.get('interval')))
        timeline = assembled(folder)
        if timeline:
            current_source = timeline.get('source', {})
            time_span = interval_label(current_source.get('interval_seconds', source.get('interval_seconds', source.get('interval'))))
            target = f'{folder.name}/integrated/index.html'
            poster = folder/'integrated/poster.png'
            n = timeline.get('frame_count', len(timeline.get('frames', [])))
            status = f'{len(timeline.get("keys", []))} KEYS · {n} FRAMES · REVIEW COPY'
            action = 'Watch the cartoon beside the archive →'
        else:
            target = f'{folder.name}/index.html'
            poster = folder/'keys/key-01.png'
            status = '6 DRAFT KEYS · ASSEMBLY PENDING'
            action = 'Open the drawings and source references →'
        note = f'<p>{e(timeline["review_note"])}</p>' if timeline.get('review_note') else ''
        card = f'<article class="gallery-card"><a href="{e(target)}"><img src="{e(href(poster,page))}" alt="{e(title)}: {"assembled cartoon" if timeline else "isolated draft"}" loading="lazy"><div class="card-body"><div class="eyebrow">{e(item.get("lot","Wave 2"))}</div><h2>{e(title)}</h2><span class="status">{e(status)}</span><p>{e(time_span)}</p>{note}<p>{action}</p></div></a></article>'
        (ready if timeline else drafts).append(card)
    films = f'<section><h2>Watch the assembled clips</h2><div class="gallery-grid">{"".join(ready)}</div></section>' if ready else ''
    queue = f'<section><h2>Still to assemble</h2><div class="gallery-grid">{"".join(drafts)}</div></section>' if drafts else ''
    inspector = '<a href="wave2-segmentation/index.html">Source / mask / drawing</a>' if (root/'shots/wave2-segmentation/index.html').is_file() else ''
    return f'''<header class="page"><div class="eyebrow">Wave 2 / moving drawings</div><h1>From archive frame<br>to moving drawing.</h1><p class="lede">{len(ready)} assembled review clips · {len(drafts)} subjects still to assemble. Watch each cartoon beside its original footage, then inspect the paired keyframes.</p></header><nav class="breadcrumbs" aria-label="Related pages"><a href="../index.html">← Rack</a>{inspector}<a href="../pages/pipeline.html">Pipeline gates</a></nav>{films}{queue}<footer>Assembled clips are review copies; final motion approval is pending. Earlier isolated drafts remain on each subject page. No training ran. Quick, Draw! contributors / Google Creative Lab, CC BY 4.0. Archive sources and reported rights are credited on each clip.</footer>'''


def build(root, head, nav, icons, write):
    root = Path(root)
    rows = discover(root)
    if not rows:
        print('Wave 2 pages: no complete draft-key packets yet.')
        return 0
    for row in rows:
        rel = f'shots/{row["folder"].name}/index.html'
        write(rel,document(row['item'].get('title',row['folder'].name),shot_body(row,root),rel,head,nav,icons))
    rel = 'shots/wave2-keyframes.html'
    write(rel,document('Wave 2 keyframes',gallery_body(rows,root),rel,head,nav,icons))
    cache = root/'shots/wave2-segmentation/data'
    if cache.is_dir():
        from build_segmentation_review import build as build_inspector
        build_inspector(cache)
    return len(rows)


if __name__ == '__main__':
    from build_pages import ROOT, HEAD, nav, icons, write
    build(ROOT, HEAD, nav, icons, write)
