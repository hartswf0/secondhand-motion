"""Stage 1 for a manual redraw: frames, camera, and a guide sheet the agent keys from.

usage: python3 tools/redraw_prep.py <category> [<category> ...]
Writes shots/<cat>-redraw/frames/fNNN.jpg (12 fps, the batch excerpt), camera.json (pan measured by
phase correlation, frame 0 = 0,0), clip.json (fps, size, key frames), and guide.png: the four key
frames with the look-lane drawing over them and a coordinate grid, for keying by eye.
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / 'batches/2026-10-20-selected-drawings'


def prep(cat):
    out = ROOT / 'shots' / f'{cat}-redraw'; fr = out / 'frames'; fr.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(B / 'subjects' / cat / 'source-excerpt.mp4'),
                    '-vf', 'fps=12', '-q:v', '5', str(fr / 'f%03d.jpg')], check=True)
    files = sorted(fr.glob('f*.jpg'))
    for i, f in enumerate(files): f.rename(fr / f'f{i:03d}.jpg')     # zero-based
    files = sorted(fr.glob('f*.jpg'))
    g = [cv2.cvtColor(cv2.imread(str(f)), cv2.COLOR_BGR2GRAY).astype(np.float32) for f in files]
    win = cv2.createHanningWindow(g[0].shape[::-1], cv2.CV_32F)
    cam = [[0.0, 0.0]]
    for a, b in zip(g[:-1], g[1:]):
        (dx, dy), resp = cv2.phaseCorrelate(a, b, win)
        if resp < 0.08: dx = dy = 0.0                                   # no confident global shift
        cam.append([round(cam[-1][0] + dx, 2), round(cam[-1][1] + dy, 2)])
    pv = json.load(open(B / 'subjects' / cat / 'preview-data.json'))
    t0 = pv['interval'][0]
    keys = [min(len(files) - 1, int(round((t - t0) * 12))) for t in pv['key_times']]
    H, W = g[0].shape
    (out / 'camera.json').write_text(json.dumps(cam))
    (out / 'clip.json').write_text(json.dumps({'category': cat, 'fps': 12, 'W': W, 'H': H, 'n': len(files), 'keys': keys,
                                               'interval': pv['interval'], 'source_title': pv['source_title']}, indent=1))
    guide(cat, out, keys, W, H)
    print(cat, 'frames', len(files), 'keys', keys, 'camera end', cam[-1])


def guide(cat, out, keys, W, H, S=1.5):
    T = json.load(open(ROOT / 'traced/traced_keys.json'))[cat]
    tiles = []
    for i, k in enumerate(keys):
        im = Image.open(out / 'frames' / f'f{k:03d}.jpg').convert('L').convert('RGB')
        im = Image.blend(im, Image.new('RGB', im.size, 'white'), 0.45).resize((int(W * S), int(H * S)))
        d = ImageDraw.Draw(im)
        for x in range(0, W + 1, 20):
            d.line([(x * S, 0), (x * S, H * S)], fill=(170, 200, 255) if x % 100 else (60, 110, 230), width=1)
            if x % 40 == 0: d.text((x * S + 2, 2), str(x), fill=(20, 60, 200))
        for y in range(0, H + 1, 20):
            d.line([(0, y * S), (W * S, y * S)], fill=(170, 200, 255) if y % 100 else (60, 110, 230), width=1)
            if y % 40 == 0: d.text((2, y * S + 2), str(y), fill=(20, 60, 200))
        for s in T['keys'][i]['strokes']:
            d.line([(x * S, y * S) for x, y in s], fill=(230, 110, 0), width=2)
        d.rectangle([0, 0, 120, 16], fill='white'); d.text((4, 2), f'key {i}  frame {k}', fill='black')
        tiles.append(im)
    w, h = tiles[0].size
    sheet = Image.new('RGB', (2 * w, 2 * h), 'white')
    for i, t in enumerate(tiles): sheet.paste(t, ((i % 2) * w, (i // 2) * h))
    sheet.save(out / 'guide.png')


if __name__ == '__main__':
    for c in sys.argv[1:]: prep(c)
