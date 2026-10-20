"""Build the offline workbench from its catalog and embedded source-photo assets."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

def main():
    data = json.loads((ROOT / 'data/catalog.json').read_text())
    data['assets'] = json.loads((ROOT / 'data/embedded-images.json').read_text())
    payload = json.dumps(data, separators=(',', ':')).replace('</', '<\\/')
    template = (ROOT / 'tools/viewer-template.html').read_text()
    assert template.count('__CATALOG_DATA__') == 1
    (ROOT / 'index.html').write_text(template.replace('__CATALOG_DATA__', payload))
    print(f'production/index.html: {len(data["items"])} clips, {len(data["assets"])} embedded reference images')

if __name__ == '__main__':
    main()
