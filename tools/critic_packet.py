"""Blind critic packet for a puppet redraw: cartoon only, no footage, no notes, no numbers.
usage: python3 tools/critic_packet.py <cat> [...]
writes shots/<cat>-redraw/critic/strip.png (8 frames, evenly spaced, numbered), keys.png (the look-lane key frames), design.png"""
import json, os, shutil, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from puppet import draw_frame
for c in sys.argv[1:]:
    d = ROOT / 'shots' / f'{c}-redraw'; S = json.load(open(d / 'shot.json')); W, H = S['W'], S['H']; n = len(S['cast']['frames'])
    (d / 'critic').mkdir(exist_ok=True); cam = S['camera']; bg = [np.array(s) for s in S['objects'][0]['strokes']]
    def frame(f):
        im = Image.new('RGB', (W, H), 'white'); draw_frame(im, [np.array(s) for s in S['cast']['frames'][f]], [s + np.array(cam[f]) for s in bg]); return im
    fr = [round(i * (n - 1) / 7) for i in range(8)]; strip = Image.new('RGB', (4 * W + 12, 2 * H + 4), 'white')
    for i, f in enumerate(fr):
        t = frame(f); ImageDraw.Draw(t).text((4, 3), str(i + 1), fill=(120, 120, 120)); strip.paste(t, ((i % 4) * (W + 4), (i // 4) * (H + 4)))
    strip.save(d / 'critic' / 'strip.png')
    keys = Image.new('RGB', (2 * W + 4, 2 * H + 4), 'white')
    for i, k in enumerate(S['cast']['look_keys']): keys.paste(frame(k), ((i % 2) * (W + 4), (i // 2) * (H + 4)))
    keys.save(d / 'critic' / 'keys.png')
    shutil.copy(ROOT / f'batches/2026-10-20-selected-drawings/subjects/{c}/design.png', d / 'critic' / 'design.png')
    print(c)
