"""Label a chosen Quick, Draw! design's strokes so the agent can group them into puppet parts.
usage: python3 tools/design_sheet.py <category> [...]  -> shots/<cat>-redraw/design-labels.png"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parent.parent
COL = [(220, 30, 30), (30, 120, 220), (20, 150, 60), (200, 120, 0), (140, 40, 180), (0, 150, 150), (120, 80, 20), (230, 60, 160), (90, 90, 90), (60, 60, 220), (160, 160, 0), (0, 0, 0), (255, 90, 0), (0, 90, 60)]
for cat in sys.argv[1:]:
    d = json.load(open(ROOT / f'batches/2026-10-20-selected-drawings/subjects/{cat}/design.json'))['drawing']
    S = 3; im = Image.new('RGB', (256 * S + 40, 256 * S + 40), 'white'); g = ImageDraw.Draw(im)
    for x in range(0, 257, 16):
        g.line([(20 + x * S, 20), (20 + x * S, 20 + 256 * S)], fill=(225, 230, 240)); g.line([(20, 20 + x * S), (20 + 256 * S, 20 + x * S)], fill=(225, 230, 240))
        if x % 32 == 0: g.text((20 + x * S, 4), str(x), fill=(90, 90, 160)); g.text((2, 20 + x * S), str(x), fill=(90, 90, 160))
    for i, s in enumerate(d):
        pts = [(20 + x * S, 20 + y * S) for x, y in zip(s[0], s[1])]; c = COL[i % len(COL)]
        g.line(pts, fill=c, width=4) if len(pts) > 1 else g.ellipse([pts[0][0] - 4, pts[0][1] - 4, pts[0][0] + 4, pts[0][1] + 4], fill=c)
        g.ellipse([pts[0][0] - 6, pts[0][1] - 6, pts[0][0] + 6, pts[0][1] + 6], outline=c, width=2)
        g.text((pts[0][0] + 7, pts[0][1] - 14), f'{i}', fill=c)
    im.save(ROOT / f'shots/{cat}-redraw/design-labels.png'); print(cat, len(d), 'strokes')
