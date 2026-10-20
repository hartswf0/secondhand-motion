"""Bring SAM masks from the browser run (tools/browser/sam_run.js) into a shot folder.

usage: python3 tools/sam_import.py <category> <file with the base64 gzip text>
writes shots/<cat>-sam/: frames/ (copied from <cat>-redraw), clip.json, masks.json {frame: [polygon, ...]},
       mask_meta.json (box source, SAM's predicted IoU and area per frame), camera.json (pan of the background,
       measured with the subject blanked out), silhouettes.png (every frame, mask over footage)
"""
import base64, gzip, json, shutil, sys
from pathlib import Path
import numpy as np, cv2
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def decode(rle, W, H):
    flat = np.zeros(W * H, bool); p = 0; v = False
    for r in rle:
        if v: flat[p:p + r] = True
        p += r; v = not v
    return flat.reshape(H, W)


def polys(mask):
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return [cv2.approxPolyDP(c, 1.2, True)[:, 0, :].tolist() for c in cs if cv2.contourArea(c) >= 30]


def camera(frames, masks):
    g = [cv2.cvtColor(cv2.imread(str(f)), cv2.COLOR_BGR2GRAY).astype(np.float32) for f in frames]
    win = cv2.createHanningWindow(g[0].shape[::-1], cv2.CV_32F); cam = [[0.0, 0.0]]
    for i in range(1, len(g)):
        a, b = g[i - 1].copy(), g[i].copy()
        for img, m in ((a, masks[i - 1]), (b, masks[i])):
            d = cv2.dilate(m.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
            if (~d).any(): img[d] = img[~d].mean()
        (dx, dy), resp = cv2.phaseCorrelate(a, b, win)
        if resp < 0.1 or abs(dx) > 40 or abs(dy) > 40: dx = dy = 0.0
        cam.append([round(cam[-1][0] + dx, 2), round(cam[-1][1] + dy, 2)])
    return cam


def main(cat, path):
    data = json.loads(gzip.decompress(base64.b64decode(open(path).read().strip())))
    src = ROOT / 'shots' / f'{cat}-redraw'; out = ROOT / 'shots' / f'{cat}-sam'; (out / 'frames').mkdir(parents=True, exist_ok=True)
    clip = json.load(open(src / 'clip.json'))
    for f in range(clip['n']): shutil.copy(src / 'frames' / f'f{f:03d}.jpg', out / 'frames' / f'f{f:03d}.jpg')
    shutil.copy(src / 'clip.json', out / 'clip.json')
    fr = sorted(data['frames'], key=lambda x: x['f'])
    masks = [decode(x['rle'], x['W'], x['H']) for x in fr]
    (out / 'masks.json').write_text(json.dumps({x['f']: polys(m) for x, m in zip(fr, masks)}, separators=(',', ':')))
    meta = {'category': cat, 'method': 'tools/browser/sam_run.js: Grounding DINO tiny box, SAM 2.1 hiera-small mask, every frame (transformers.js 4.3.1, WebGPU)',
            'frames': [{k: x[k] for k in ('f', 'box', 'from', 'iou', 'area')} for x in fr],
            'coverage': round(sum(1 for m in masks if m.sum() > 30) / len(masks), 3),
            'mean_iou': round(float(np.mean([x['iou'] for x in fr])), 3),
            'detected': sum(1 for x in fr if x['from'].startswith('dino')), 'n': len(fr)}
    (out / 'mask_meta.json').write_text(json.dumps(meta, indent=1))
    (out / 'camera.json').write_text(json.dumps(camera([out / 'frames' / f'f{x["f"]:03d}.jpg' for x in fr], masks)))
    # contact sheet: every other frame, silhouette in red over the footage
    sel = list(range(0, len(fr), max(1, len(fr) // 16)))[:16]; W, H = fr[0]['W'], fr[0]['H']; tw, th = W // 2, H // 2
    sheet = Image.new('RGB', (4 * tw, 4 * th), 'white')
    for n, i in enumerate(sel):
        im = cv2.imread(str(out / 'frames' / f'f{fr[i]["f"]:03d}.jpg')); ov = im.copy(); ov[masks[i]] = (40, 40, 220)
        im = cv2.addWeighted(im, 0.55, ov, 0.45, 0); cv2.putText(im, str(fr[i]['f']), (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        sheet.paste(Image.fromarray(im[:, :, ::-1]).resize((tw, th)), ((n % 4) * tw, (n // 4) * th))
    sheet.save(out / 'silhouettes.png')
    print(cat, 'frames', meta['n'], 'detected', meta['detected'], 'coverage', meta['coverage'], 'mean SAM IoU', meta['mean_iou'])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
