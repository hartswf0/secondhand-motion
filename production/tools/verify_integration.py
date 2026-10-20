"""Validate the catalog, embedded photographs, existing art links and planning counts."""
from pathlib import Path
from collections import Counter
import base64, io, json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

def main():
    data = json.loads((ROOT / 'data/catalog.json').read_text())
    images = json.loads((ROOT / 'data/embedded-images.json').read_text())
    assert len(data['items']) == len({x['clip_id'] for x in data['items']}) == 100
    assert len({x['category'] for x in data['items']}) == 100
    keys = [key for x in data['items'] for key in x['keys']]
    assert len(keys) == 40
    decoded = 0
    for uri in images.values():
        assert uri.startswith('data:image/jpeg;base64,')
        with Image.open(io.BytesIO(base64.b64decode(uri.split(',', 1)[1], validate=True))) as im:
            im.load()
        decoded += 1
    def check(ref):
        if ref in images:
            return
        p = (ROOT / ref).resolve()
        assert p.is_relative_to(ROOT.parent.resolve()) and p.is_file(), ref
        if p.suffix == '.png':
            with Image.open(p) as im:
                im.load()
    refs = []
    for item in data['items']:
        check(item['thumbnail'])
        for key in item['keys']:
            for name in ('source_image', 'drawing_image', 'first_image'):
                check(key[name])
        for name in ('source_video', 'comparison_video'):
            if item.get(name):
                check(item[name])
        for ref in item.get('plan', {}).get('proposed_sources', []):
            check(ref['source_image'])
            assert ref['status'] == 'reference_only_not_authored_or_approved'
            refs.append(ref)
    assert Counter(x['kind'] for x in refs) == {'pose_key': 39, 'breakdown': 24, 'procedural_check': 3}
    s = data['frame_plan']['current_ten_totals']
    assert s['total_authored_drawing_budget_including_existing'] == 103
    snapshot = json.loads((ROOT / 'data/queue-snapshot.json').read_text())
    assert sum(x['count'] for x in snapshot['counts'] if x['stage'] == 'source_review' and x['state'] == 'done') == 2
    assert '__CATALOG_DATA__' not in (ROOT / 'index.html').read_text()
    result = {'passed': True, 'clips': 100, 'existing_authored_keys': 40,
              'embedded_images_decoded': decoded, 'next_source_references': len(refs),
              'new_authored_drawings': 0, 'new_motion_approvals': 0}
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
