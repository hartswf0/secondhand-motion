from pathlib import Path
import json
from PIL import Image
from build_gallery import quadrants,sheet,save_image
R=Path(__file__).resolve().parent
for item in json.loads((R/'data/curation.json').read_text())['items']:
 f=R/'subjects'/item['category'];art=quadrants(f/f"revisions/keys-{item['selected_revision']}.png");photos=quadrants(f/'source-keys.png')
 for i,im in enumerate(art):save_image(im,f/f'art-key-{i}.png')
 for i,im in enumerate(photos):save_image(im,f/f'source-key-{i}.png')
 save_image(sheet(art,2,(384,288)),f/'selected-keys.png');save_image(sheet([im for pair in zip(photos,art) for im in pair],2,(384,288)),f/'key-comparison.png')
for p in R.rglob('*'):
 if p.suffix.lower() in ['.png','.jpg']:
  with Image.open(p) as im:im.load()
print('All project PNG/JPEG files decode after atomic export regeneration.')
