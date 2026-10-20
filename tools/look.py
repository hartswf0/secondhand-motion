"""Key frames with a light labelled grid, for placing joints by eye.
usage: python3 tools/look.py <cat> [scale=1.6] [frame ...]  (frames default to the keys)  -> shots/<cat>-redraw/look.png (2x2 keys, frame coordinates on the grid)"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parent.parent
cat = sys.argv[1]; S = float(sys.argv[2]) if len(sys.argv) > 2 else 1.6
d = ROOT / 'shots' / f'{cat}-redraw'; clip = json.load(open(d / 'clip.json')); tiles = []
frames = [int(a) for a in sys.argv[3:]] or clip['keys']
for i, f in enumerate(frames):
    im = Image.open(d / 'frames' / f'f{f:03d}.jpg').convert('RGB'); W, H = im.size
    im = im.resize((int(W * S), int(H * S)), Image.LANCZOS); dr = ImageDraw.Draw(im, 'RGBA')
    for x in range(20, W, 20):
        dr.line([(x * S, 0), (x * S, im.height)], fill=(255, 230, 0, 150 if x % 100 == 0 else 60), width=1)
        dr.text((x * S + 2, 2), str(x), fill=(255, 240, 0, 255))
    for y in range(20, H, 20):
        dr.line([(0, y * S), (im.width, y * S)], fill=(255, 230, 0, 150 if y % 100 == 0 else 60), width=1)
        dr.text((2, y * S + 2), str(y), fill=(255, 240, 0, 255))
    dr.rectangle([0, im.height - 14, 90, im.height], fill='white'); dr.text((3, im.height - 13), f'f{f}', fill='black'); tiles.append(im)
w, h = tiles[0].size; rows = (len(tiles) + 1) // 2; sh = Image.new('RGB', (2 * w + 4, rows * (h + 4)), 'white')
for i, t in enumerate(tiles): sh.paste(t, ((i % 2) * (w + 4), (i // 2) * (h + 4)))
sh.save(d / 'look.png'); print(sh.size)
