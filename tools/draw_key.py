"""Sheets for drawing keys by hand over the footage (see tools/drawn.py).

usage:
  python3 tools/draw_key.py frames <slug>            every frame of the clip, small and numbered, with the drawing as it
                                                    stands in black: for choosing which frames are keys
                                                    -> shots/<slug>/drawn/frames-N.png
  python3 tools/draw_key.py key <slug> <f> [...]     the frame enlarged 2x with a grid labelled in frame pixels, the
                                                    rig's drawing at that frame with every stroke numbered (colour per
                                                    stroke) and every point indexed, the doodle beside it. Writes the
                                                    template shots/<slug>/drawn/k###.json (rig drawing, frame pixels)
                                                    if it does not exist. -> shots/<slug>/drawn/key-###.png
  python3 tools/draw_key.py check <slug> <f> [...]   the drawn key in blue over the frame, the rig drawing faint, the
                                                    doodle beside it, and the drawn key alone on white
                                                    -> shots/<slug>/drawn/check-###.png
Edit k###.json by moving points (keep the stroke count and the points per stroke; a stroke may be resampled), and
add "extra" strokes only for a part the doodle has no stroke for. Then rebuild: python3 tools/subject.py build <slug>.
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parent.parent
COLS = [(220, 40, 40), (30, 110, 220), (20, 150, 60), (200, 110, 0), (150, 40, 180), (0, 150, 160), (120, 120, 0), (200, 40, 140), (90, 60, 30), (60, 60, 200)]


def shot(slug):
    g = ROOT / 'shots' / f'{slug}-gwp'; S = json.load(open(g / 'shot.json'))
    rig = json.load(open(g / 'rig_frames.json')) if (g / 'rig_frames.json').exists() else S['cast']['frames']
    return g, S, rig


def doodle(slug, size):
    p = ROOT / 'shots' / slug / 'design.png'
    return Image.open(p).convert('RGB').resize((size, size)) if p.exists() else Image.new('RGB', (size, size), 'white')


def poly(g, s, k, col, w):
    pts = [(x * k, y * k) for x, y in s]
    if len(pts) > 1: g.line(pts, fill=col, width=w)
    elif pts: g.ellipse([pts[0][0] - 3, pts[0][1] - 3, pts[0][0] + 3, pts[0][1] + 3], fill=col)


def frames_sheet(slug):
    g, S, _ = shot(slug); n = len(S['cast']['frames']); W, H = S['W'], S['H']; d = ROOT / 'shots' / slug / 'drawn'; d.mkdir(parents=True, exist_ok=True)
    tw, th = W // 2, H // 2; cols = 8; per = 48
    for page in range((n + per - 1) // per):
        fs = list(range(page * per, min(n, (page + 1) * per))); rows = (len(fs) + cols - 1) // cols
        im = Image.new('RGB', (cols * (tw + 4), rows * (th + 16)), 'white'); dr = ImageDraw.Draw(im)
        for i, f in enumerate(fs):
            x, y = (i % cols) * (tw + 4), (i // cols) * (th + 16)
            fr = Image.open(g / S['footage'][f]).convert('RGB').resize((tw, th)); fd = ImageDraw.Draw(fr)
            for s in S['cast']['frames'][f]: poly(fd, s, 0.5, (0, 0, 0), 1)
            im.paste(fr, (x, y + 14)); mark = ' K' if f in S['cast']['keys'] else ''
            dr.text((x + 2, y + 1), f'{f}{mark}', fill=(200, 0, 0) if mark else (0, 0, 0))
        im.save(d / f'frames-{page + 1}.png')
    print('frames sheets in', d)


def key_sheet(slug, f):
    g, S, rig = shot(slug); W, H = S['W'], S['H']; d = ROOT / 'shots' / slug / 'drawn'; d.mkdir(parents=True, exist_ok=True); k = 2
    tp = d / f'k{f:03d}.json'
    if not tp.exists():
        json.dump({'why': '', 'strokes': [[[round(x, 1), round(y, 1)] for x, y in s] for s in rig[f]], 'extra': {}}, open(tp, 'w'))
    fr = Image.open(g / S['footage'][f]).convert('RGB').resize((W * k, H * k))
    fr = Image.blend(fr, Image.new('RGB', fr.size, 'white'), 0.35); dr = ImageDraw.Draw(fr)
    for x in range(0, W, 16): dr.line([(x * k, 0), (x * k, H * k)], fill=(200, 200, 200) if x % 32 else (150, 150, 150), width=1)
    for y in range(0, H, 16): dr.line([(0, y * k), (W * k, y * k)], fill=(200, 200, 200) if y % 32 else (150, 150, 150), width=1)
    for x in range(0, W, 32): dr.text((x * k + 2, 2), str(x), fill=(90, 90, 90))
    for y in range(32, H, 32): dr.text((2, y * k + 2), str(y), fill=(90, 90, 90))
    K = json.load(open(tp))
    for i, s in enumerate(K['strokes']):
        c = COLS[i % len(COLS)]; poly(dr, s, k, c, 3)
        step = 1 if len(s) <= 12 else 3   # long strokes: every third point labelled
        for j, (x, y) in enumerate(s):
            if j % step == 0 or j == len(s) - 1: dr.text((x * k + 3, y * k - 10), str(j), fill=c)
        dr.text((s[0][0] * k - 14, s[0][1] * k - 14), f'S{i}', fill=c)
    for nm, s in K.get('extra', {}).items():
        poly(dr, s, k, (0, 0, 0), 3); dr.text((s[0][0] * k + 4, s[0][1] * k + 4), f'+{nm}', fill=(0, 0, 0))
    out = Image.new('RGB', (W * k + 260, H * k), 'white'); out.paste(fr, (0, 0)); out.paste(doodle(slug, 250), (W * k + 5, 5))
    ImageDraw.Draw(out).text((W * k + 8, 262), f'frame {f}\nthe doodle\n(k{f:03d}.json)', fill=(0, 0, 0))
    out.save(d / f'key-{f:03d}.png'); print(d / f'key-{f:03d}.png')


def check(slug, f):
    g, S, rig = shot(slug); W, H = S['W'], S['H']; d = ROOT / 'shots' / slug / 'drawn'; k = 2
    K = json.load(open(d / f'k{f:03d}.json'))
    fr = Image.open(g / S['footage'][f]).convert('RGB').resize((W * k, H * k)); dr = ImageDraw.Draw(fr)
    for s in rig[f]: poly(dr, s, k, (170, 170, 170), 2)
    for s in K['strokes'] + list(K.get('extra', {}).values()): poly(dr, s, k, (20, 60, 230), 3)
    alone = Image.new('RGB', (W * k, H * k), 'white'); da = ImageDraw.Draw(alone)
    for s in K['strokes'] + list(K.get('extra', {}).values()): poly(da, s, k, (20, 20, 20), 3)
    out = Image.new('RGB', (W * k * 2 + 260, H * k), 'white'); out.paste(fr, (0, 0)); out.paste(alone, (W * k, 0)); out.paste(doodle(slug, 250), (W * k * 2 + 5, 5))
    out.save(d / f'check-{f:03d}.png'); print(d / f'check-{f:03d}.png')


if __name__ == '__main__':
    cmd, slug, *fs = sys.argv[1:]
    if cmd == 'frames': frames_sheet(slug)
    else:
        for f in fs: (key_sheet if cmd == 'key' else check)(slug, int(f))
