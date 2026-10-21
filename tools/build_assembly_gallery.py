"""Build one offline comparison player for the integrated archive drawings.

Only complete integrated assemblies with an item record enter this gallery.
This is a viewing surface, not an acceptance or training-eligibility gate.
"""
from pathlib import Path
import json

from build_pages import ROOT, HEAD, nav, icons, write


def render(rows, rel, title, template, batch_nav=""):
    content = template.replace("__DATA__", json.dumps(rows, separators=(",", ":")).replace("</", "<\\/"))
    content = content.replace("__BATCH_NAV__", batch_nav)
    if rel.endswith("batch-25.html"):
        content = content.replace("Watch the motion<br>change hands.", "Twenty-five more<br>moving drawings.")
    html = HEAD.replace("__ICONS__", icons(rel)) + "<title>" + title + " · Secondhand Motion</title>"
    write(rel, html + '<body><div class="wrap">' + nav(rel) + content + '</div></body></html>')


def build():
    rows = []
    for folder in sorted((ROOT/'shots').iterdir()):
        base = folder/'integrated'
        required = ['shot.json', 'index.html', 'poster.png', 'cartoon.mp4',
                    'source-excerpt.mp4', 'comparison.mp4']
        if not (folder/'item.json').is_file() or not all((base/n).is_file() for n in required):
            continue
        item = json.loads((folder/'item.json').read_text())
        shot = json.loads((base/'shot.json').read_text())
        rows.append(dict(slug=folder.name, title=item['title'], lot=item['lot'],
                         wave=item.get('wave', 0), frames=shot['frame_count'],
                         fps=shot['fps'], keys=len(shot['keys']),
                         note=shot.get('review_note', 'Playback approval pending.'),
                         summary=shot.get('assembly_summary', ''),
                         W=shot['W'], H=shot['H']))
    rows.sort(key=lambda row: (-row['wave'], -int(row['lot'].rsplit('-', 1)[-1])))
    template = (ROOT/'tools/templates/assembly_gallery.html').read_text()
    manifest_path = ROOT/'production/batches/2026-10-20-batch25/manifest.json'
    batch = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    slugs = {r['slug'] for r in batch.get('subjects', [])}
    batch_rows = [r for r in rows if r['slug'] in slugs]
    complete = len(batch_rows) == batch.get('target_count') == 25
    render(rows, 'shots/moving-drawings.html', 'Moving drawings', template,
           '<a href="batch-25.html">New batch: 25 clips</a>' if complete else '')
    if complete:
        render(batch_rows, 'shots/batch-25.html', 'Twenty-five more moving drawings', template,
               '<a href="moving-drawings.html">All moving drawings</a>')
    print(f'Moving drawings: {len(rows)} integrated review clips')


if __name__ == '__main__':
    build()
