"""Stage 1 for a wave-2 shot, run on GitHub's machines (they can reach the archive's media host; this
workspace cannot): frames, SAM 2.1 masks and Depth Anything V2 depth for the key interval.

usage (CI): python3 tools/wave2_track.py --slug pig --out out/pig
Reads shots/<slug>/source.json and keyplan.json. Cuts the clip from the first key time - 0.1 s to the last
+ 0.1 s at 12 fps, 384 px wide. Grounding DINO (IDEA-Research/grounding-dino-tiny) finds the subject from a
short text label on every frame; SAM 2.1 (facebook/sam2.1-hiera-small) turns the box into a mask (the
highest predicted IoU of its three). Depth Anything V2 Small gives relative depth per frame (saved 192 px
wide, 8-bit, near = bright). Writes frames/, depth/, track.json (RLE masks, same format as the browser
runner tools/browser/sam_run.js) and clip.json.
"""
import argparse, json, subprocess, time
from pathlib import Path
from urllib.request import Request, urlopen
import numpy as np
from PIL import Image

LABEL = {'flying-saucer': 'a spacecraft.', 'raccoon': 'a raccoon.', 'hurricane': 'a breaking wave.', 'tornado': 'a tornado.',
         'rain': 'a puddle.', 'mosquito': 'a mosquito.', 'pig': 'a pig.', 'see-saw': 'a seesaw.', 'tractor': 'a tractor.', 'fan': 'a fan.'}


def fetch(url, path):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 SecondhandMotion/1.0', 'Referer': 'https://www.movingimagearchive.com/'})
    with urlopen(req, timeout=60) as r, open(path, 'wb') as f:
        while True:
            b = r.read(1 << 20)
            if not b: break
            f.write(b)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--slug', required=True); ap.add_argument('--out', required=True); a = ap.parse_args()
    src = json.load(open(f'shots/{a.slug}/source.json')); src = src.get('source', src)
    kp = json.load(open(f'shots/{a.slug}/keyplan.json')); times = [k['time'] for k in kp['keys']]
    out = Path(a.out); (out / 'frames').mkdir(parents=True, exist_ok=True); (out / 'depth').mkdir(exist_ok=True)
    clip = out / 'clip.mp4'; fetch(src['video_url'], clip)
    t0 = max(0.0, times[0] - 0.1); dur = times[-1] + 0.1 - t0
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{t0:.3f}', '-i', str(clip), '-t', f'{dur:.3f}',
                    '-vf', 'fps=12,scale=384:-2', '-q:v', '3', str(out / 'frames' / 'f%03d.jpg')], check=True)
    fs = sorted((out / 'frames').glob('f*.jpg'))
    for i, f in enumerate(fs): f.rename(out / 'frames' / f'g{i:03d}.jpg')
    for i in range(len(fs)): (out / 'frames' / f'g{i:03d}.jpg').rename(out / 'frames' / f'f{i:03d}.jpg')
    n = len(fs); W, H = Image.open(out / 'frames' / 'f000.jpg').size
    keys = [min(n - 1, round((t - t0) * 12)) for t in times]
    json.dump({'slug': a.slug, 'n': n, 'W': W, 'H': H, 'fps': 12, 't0': round(t0, 3), 'key_times': times, 'keys': keys,
               'clip_id': src.get('clip_id'), 'label': LABEL[a.slug]}, open(out / 'clip.json', 'w'), indent=1)
    import torch
    from transformers import pipeline, Sam2Processor, Sam2Model
    det = pipeline('zero-shot-object-detection', model='IDEA-Research/grounding-dino-tiny')
    proc = Sam2Processor.from_pretrained('facebook/sam2.1-hiera-small'); sam = Sam2Model.from_pretrained('facebook/sam2.1-hiera-small').eval()
    depth = pipeline('depth-estimation', model='depth-anything/Depth-Anything-V2-Small-hf')
    res = []; prev = None; t_start = time.time()
    for f in range(n):
        img = Image.open(out / 'frames' / f'f{f:03d}.jpg').convert('RGB')
        d = det(img, candidate_labels=[LABEL[a.slug]], threshold=0.2)
        if d:
            d.sort(key=lambda x: -x['score']); b = d[0]['box']; box = [b['xmin'], b['ymin'], b['xmax'], b['ymax']]; frm = f"dino {d[0]['score']:.2f}"; prev = box
        elif prev: box, frm = prev, 'previous box'
        else: box, frm = [0, 0, W - 1, H - 1], 'whole frame'
        inp = proc(images=img, input_boxes=[[box]], return_tensors='pt')
        with torch.no_grad(): o = sam(**inp)
        ms = proc.post_process_masks(o.pred_masks, inp['original_sizes'])[0]   # (1, 3, H, W)
        sc = o.iou_scores[0, 0].numpy(); bi = int(np.argmax(sc)); m = ms[0, bi].numpy().astype(np.uint8).ravel()
        ch = np.flatnonzero(np.diff(np.r_[0, m, 1 - m[-1]])) if m.size else []
        runs = np.diff(np.r_[0, ch]).tolist() if len(ch) else [int(m.size)]
        res.append({'f': f, 'box': [round(v) for v in box], 'from': frm, 'iou': round(float(sc[bi]), 3), 'area': int(m.sum()), 'W': W, 'H': H, 'rle': runs})
        dp = depth(img)['depth'].resize((192, round(192 * H / W))); dp.save(out / 'depth' / f'f{f:03d}.png')
        print(f, frm, round(float(sc[bi]), 3), int(m.sum()), f'{time.time() - t_start:.0f}s', flush=True)
    json.dump({'frames': res}, open(out / 'track.json', 'w'))
    clip.unlink()


if __name__ == '__main__':
    main()
