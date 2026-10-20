"""The chosen doodle drawn large with every stroke numbered and every vertex indexed, for writing a rig spec
(which vertices make the head, a leg, a wheel; where the joints are).
usage: python3 tools/doodle_sheet.py <design.json> <out.png> [mirror]"""
import json, sys
from PIL import Image, ImageDraw
d = json.load(open(sys.argv[1])); dr = d['drawing'] if not isinstance(d['drawing'], str) else json.loads(d['drawing'])
mir = len(sys.argv) > 3; S = 3.0; im = Image.new('RGB', (int(256 * S) + 80, int(256 * S) + 80), 'white'); g = ImageDraw.Draw(im)
cols = [(200, 30, 30), (30, 110, 200), (20, 150, 70), (170, 90, 0), (140, 40, 170), (0, 140, 150), (90, 90, 90)]
for x in range(0, 257, 32):
    g.line([(40 + x * S, 40), (40 + x * S, 40 + 256 * S)], fill=(230, 230, 240)); g.text((42 + x * S, 26), str(x), fill=(150, 150, 170))
    g.line([(40, 40 + x * S), (40 + 256 * S, 40 + x * S)], fill=(230, 230, 240)); g.text((4, 42 + x * S), str(x), fill=(150, 150, 170))
for i, s in enumerate(dr):
    P = [((255 - u) if mir else u, v) for u, v in zip(*s)]; c = cols[i % len(cols)]
    if len(P) > 1: g.line([(40 + u * S, 40 + v * S) for u, v in P], fill=c, width=3)
    for j, (u, v) in enumerate(P):
        g.ellipse([40 + u * S - 3, 40 + v * S - 3, 40 + u * S + 3, 40 + v * S + 3], fill=c)
        if j == 0 or j == len(P) - 1 or j % 3 == 0: g.text((40 + u * S + 4, 40 + v * S - 12), f'{i}.{j}', fill=c)
im.save(sys.argv[2])
