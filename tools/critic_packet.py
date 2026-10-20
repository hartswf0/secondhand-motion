"""Blind critic packet for a puppet redraw: cartoon only, no footage, no notes, no numbers.
usage: python3 tools/critic_packet.py <cat> [...] [--suffix=redraw|sam]
writes shots/<cat>-<suffix>/critic/strip.png (8 frames, evenly spaced, numbered), footage.png (the source at the same 8 frames),
keys.png (four key frames), design.png. Scenery objects slide with the camera at their plane's depth."""
import json, os, shutil, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from puppet import draw_frame
SUF = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--suffix=")), "redraw")
for c in [a for a in sys.argv[1:] if not a.startswith("--")]:
    d = ROOT / 'shots' / f'{c}-{SUF}'; S = json.load(open(d / 'shot.json')); W, H = S['W'], S['H']; n = len(S['cast']['frames'])
    (d / 'critic').mkdir(exist_ok=True); cam = S['camera']
    zr = S.get('z_ref', 3); zof = {p['id']: p['z'] for p in S.get('planes', [])}
    def bgs(f):   # every scenery object, slid by the camera at its plane's depth
        return [np.array(s) + np.array(cam[f]) * (zr / zof.get(o['plane'], zr)) for o in S['objects'] for s in o['strokes'] if len(s) > 1]
    def frame(f):
        im = Image.new('RGB', (W, H), 'white')
        if S['masks'][f]:   # cel: the silhouette painted under the character
            from PIL import ImageDraw as D2
            m = Image.new('L', (W, H), 0); g2 = D2.Draw(m)
            for p in S['masks'][f]:
                if len(p) > 2: g2.polygon([tuple(q) for q in p], fill=255)
            draw_frame(im, [], bgs(f)); im.paste((255, 255, 255), mask=m); draw_frame(im, [np.array(s) for s in S['cast']['frames'][f]], [])
            return im
        draw_frame(im, [np.array(s) for s in S['cast']['frames'][f]], bgs(f)); return im
    NF = 16 if '--dense' in sys.argv else 8
    fr = [round(i * (n - 1) / (NF - 1)) for i in range(NF)]; rows = NF // 4; strip = Image.new('RGB', (4 * W + 12, rows * H + 4 * (rows - 1)), 'white')
    for i, f in enumerate(fr):
        t = frame(f); ImageDraw.Draw(t).text((4, 3), str(i + 1), fill=(120, 120, 120)); strip.paste(t, ((i % 4) * (W + 4), (i // 4) * (H + 4)))
    strip.save(d / 'critic' / 'strip.png')
    foot = Image.new('RGB', (4 * W + 12, rows * H + 4 * (rows - 1)), 'white')   # the source footage at the same 8 frames
    for i, f in enumerate(fr):
        t = Image.open(d / S['footage'][f]).convert('RGB') if not S['footage'][f].startswith('data:') else Image.new('RGB', (W, H), 'gray')
        ImageDraw.Draw(t).text((4, 3), str(i + 1), fill=(255, 255, 0)); foot.paste(t, ((i % 4) * (W + 4), (i // 4) * (H + 4)))
    foot.save(d / 'critic' / 'footage.png')
    keys = Image.new('RGB', (2 * W + 4, 2 * H + 4), 'white')
    lk = S['cast'].get('look_keys') or [S['cast']['keys'][round(i * (len(S['cast']['keys']) - 1) / 3)] for i in range(4)]
    for i, k in enumerate(lk): keys.paste(frame(k), ((i % 2) * (W + 4), (i // 2) * (H + 4)))
    keys.save(d / 'critic' / 'keys.png')
    dp = ROOT / f'batches/2026-10-20-selected-drawings/subjects/{c}/design.png'
    shutil.copy(dp if dp.exists() else ROOT / 'shots' / c / 'design.png', d / 'critic' / 'design.png')
    print(c)
