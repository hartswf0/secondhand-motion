"""Build one offline comparison player for the integrated archive drawings.

Only complete integrated assemblies with an item record enter this gallery.
This is a viewing surface, not an acceptance or training-eligibility gate.
"""
from pathlib import Path
import json

from build_pages import ROOT, HEAD, nav, icons, write


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
    content = template.replace('__DATA__', json.dumps(rows, separators=(',', ':')).replace('</', '<\\/'))
    rel = 'shots/moving-drawings.html'
    html = HEAD.replace('__ICONS__', icons(rel)) + '<title>Moving drawings · Secondhand Motion</title>'
    write(rel, html + '<body><div class="wrap">' + nav(rel) + content + '</div></body></html>')
    print(f'Moving drawings: {len(rows)} integrated review clips')


if __name__ == '__main__':
    build()
