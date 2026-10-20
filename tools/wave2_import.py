"""Bring a wave-2 subject's CI output (branch wave2-track/<slug>: frames, SAM masks, depth) into
shots/<slug>-sam/, the same layout the wave-1 SAM shots use, plus depth/ and depth.json.

usage: python3 tools/wave2_import.py <slug> [...]   (after: git fetch origin 'refs/heads/wave2-track/*:refs/remotes/origin/wave2-track/*')
depth.json: per frame, the median relative depth (0 far .. 1 near) inside the subject's mask and outside it,
and per scenery band (top, middle, bottom third of the frame outside the mask), used to set plane depths.
"""
import json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np, cv2
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from sam_import import decode, polys, camera


# frames to keep, [first, last): cuts found by frame differencing and checked by eye (fan: a different shot in
# the last frame; flying saucer: the first frame is the previous shot)
TRIM = {'fan': (0, 38), 'flying-saucer': (1, 29)}


def run(slug):
    out = ROOT / 'shots' / f'{slug}-sam'; out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        subprocess.run(f'git -C {ROOT} archive origin/wave2-track/{slug} | tar -x -C {t}', shell=True, check=True)
        t = Path(t)
        for sub in ('frames', 'depth'):
            (out / sub).mkdir(exist_ok=True)
            for f in (t / sub).glob('*'): (out / sub / f.name).write_bytes(f.read_bytes())
        clip = json.load(open(t / 'clip.json')); tr = json.load(open(t / 'track.json'))
        if slug in TRIM:
            a, b = TRIM[slug]
            for sub in ('frames', 'depth'):
                for f in sorted((out / sub).glob('f*')): f.unlink()
                for i in range(a, b):
                    ext = 'jpg' if sub == 'frames' else 'png'
                    (out / sub / f'f{i - a:03d}.{ext}').write_bytes((t / sub / f'f{i:03d}.{ext}').read_bytes())
            tr['frames'] = [dict(x, f=x['f'] - a) for x in tr['frames'] if a <= x['f'] < b]
            clip['n'] = b - a; clip['t0'] = round(clip['t0'] + a / 12, 3); clip['trim'] = [a, b]
            clip['keys'] = [min(b - a - 1, max(0, k - a)) for k in clip['keys']]
    kp = json.load(open(ROOT / 'shots' / slug / 'keyplan.json'))
    clip.update({'category': slug, 'source_title': json.load(open(ROOT / 'shots' / slug / 'source.json')).get('source', {}).get('source_title', 'Moving Image Archive')})
    (out / 'clip.json').write_text(json.dumps(clip, indent=1))
    fr = sorted(tr['frames'], key=lambda x: x['f']); masks = [decode(x['rle'], x['W'], x['H']) for x in fr]
    (out / 'masks.json').write_text(json.dumps({x['f']: polys(m) for x, m in zip(fr, masks)}, separators=(',', ':')))
    meta = {'category': slug, 'method': 'tools/wave2_track.py on GitHub Actions: Grounding DINO tiny box from "' + clip['label'] + '", SAM 2.1 hiera-small mask, every frame (transformers 4.57.1, CPU); Depth Anything V2 Small per frame',
            'frames': [{k: x[k] for k in ('f', 'box', 'from', 'iou', 'area')} for x in fr],
            'coverage': round(sum(1 for m in masks if m.sum() > 30) / len(masks), 3), 'mean_iou': round(float(np.mean([x['iou'] for x in fr])), 3),
            'detected': sum(1 for x in fr if x['from'].startswith('dino')), 'n': len(fr)}
    (out / 'mask_meta.json').write_text(json.dumps(meta, indent=1))
    (out / 'camera.json').write_text(json.dumps(camera([out / 'frames' / f'f{x["f"]:03d}.jpg' for x in fr], masks)))
    W, H = clip['W'], clip['H']; dj = []
    for x, m in zip(fr, masks):
        dp = np.array(Image.open(out / 'depth' / f'f{x["f"]:03d}.png').convert('L').resize((W, H))).astype(float) / 255
        bands = {}
        for name, (a, b) in {'top': (0, H // 3), 'middle': (H // 3, 2 * H // 3), 'bottom': (2 * H // 3, H)}.items():
            sel = ~m[a:b]; bands[name] = round(float(np.median(dp[a:b][sel])), 3) if sel.any() else None
        dj.append({'f': x['f'], 'subject': round(float(np.median(dp[m])), 3) if m.any() else None, 'scene': round(float(np.median(dp[~m])), 3), **bands})
    (out / 'depth.json').write_text(json.dumps(dj, indent=0))
    sel = list(range(0, len(fr), max(1, len(fr) // 16)))[:16]; tw, th = W // 2, H // 2
    sheet = Image.new('RGB', (4 * tw, 4 * th), 'white')
    for n, i in enumerate(sel):
        im = cv2.imread(str(out / 'frames' / f'f{fr[i]["f"]:03d}.jpg')); ov = im.copy(); ov[masks[i]] = (40, 40, 220)
        im = cv2.addWeighted(im, 0.55, ov, 0.45, 0); cv2.putText(im, str(fr[i]['f']), (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        sheet.paste(Image.fromarray(im[:, :, ::-1]).resize((tw, th)), ((n % 4) * tw, (n // 4) * th))
    sheet.save(out / 'silhouettes.png')
    print(slug, 'frames', meta['n'], 'keys', clip['keys'], 'detected', meta['detected'], 'coverage', meta['coverage'], 'mean SAM IoU', meta['mean_iou'])


if __name__ == '__main__':
    for s in sys.argv[1:]: run(s)
