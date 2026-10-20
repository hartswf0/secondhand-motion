"""Zoomed key frames with a fine grid, for placing joints by eye.
usage: python3 tools/zoom.py <cat> x0 y0 x1 y1 [scale] [--ink to overlay the look-lane trace]  -> shots/<cat>-redraw/zoom.png"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if not a.startswith('--')]
cat = args[0]; x0, y0, x1, y1 = map(int, args[1:5]); S = float(args[5]) if len(args) > 5 else 2.5
d = ROOT / 'shots' / f'{cat}-redraw'; clip = json.load(open(d / 'clip.json'))
T = json.load(open(ROOT / 'traced/traced_keys.json'))[cat]['keys']
tiles = []
for i, k in enumerate(clip['keys']):
    im = Image.open(d / 'frames' / f'f{k:03d}.jpg').convert('RGB').crop((x0, y0, x1, y1)).resize((int((x1 - x0) * S), int((y1 - y0) * S)))
    g = ImageDraw.Draw(im)
    if '--ink' in sys.argv:
      for s in T[i]['strokes']: g.line([((x - x0) * S, (y - y0) * S) for x, y in s], fill=(255, 140, 0), width=1)
    for x in range((x0 // 10) * 10, x1 + 1, 10):
        g.line([((x - x0) * S, 0), ((x - x0) * S, im.height)], fill=(80, 140, 255) if x % 50 else (0, 60, 255), width=1)
        if x % 20 == 0: g.text(((x - x0) * S + 2, 2), str(x), fill=(0, 40, 200))
    for y in range((y0 // 10) * 10, y1 + 1, 10):
        g.line([(0, (y - y0) * S), (im.width, (y - y0) * S)], fill=(80, 140, 255) if y % 50 else (0, 60, 255), width=1)
        if y % 20 == 0: g.text((2, (y - y0) * S + 2), str(y), fill=(0, 40, 200))
    g.rectangle([0, im.height - 14, 70, im.height], fill='white'); g.text((3, im.height - 13), f'key {i}', fill='black'); tiles.append(im)
w, h = tiles[0].size; sh = Image.new('RGB', (2 * w + 6, 2 * h + 6), 'white')
for i, t in enumerate(tiles): sh.paste(t, ((i % 2) * (w + 6), (i // 2) * (h + 6)))
sh.save(d / 'zoom.png'); print(sh.size)
