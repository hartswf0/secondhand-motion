"""Stage A for a new subject, run on GitHub's machines (they reach the archive's media host): everything an
agent needs to choose the interval and the doodle, in one pass.

usage (CI): python3 tools/survey.py --slug cow --wave data/wave3.json --out out/cow
Writes: sheet.jpg (the whole clip, one frame every 0.25 s, numbered with its time), cuts.json (frame-difference
spikes, candidate cuts), doodles.jpg + doodles.json (the first 40 recognized Quick, Draw! drawings of the
category with 4 to 20 strokes, numbered, raw strokes kept), clip.json (duration, size, fps).
"""
import argparse, json, subprocess, sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
from wave2_track import fetch


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--slug'); ap.add_argument('--wave'); ap.add_argument('--out'); a = ap.parse_args()
    S = next(s for s in json.load(open(a.wave))['subjects'] if s['slug'] == a.slug); out = Path(a.out); (out / 'f').mkdir(parents=True, exist_ok=True)
    clip = out / 'clip.mp4'; fetch(S['video_url'], clip)
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(clip), '-vf', 'fps=4,scale=192:-2', '-q:v', '4', str(out / 'f' / 'f%04d.jpg')], check=True)
    fs = sorted((out / 'f').glob('*.jpg')); ims = [Image.open(f).convert('RGB') for f in fs]; w, h = ims[0].size
    cols = 8; sheet = Image.new('RGB', (cols * w, ((len(ims) + cols - 1) // cols) * (h + 14)), 'white'); d = ImageDraw.Draw(sheet)
    for i, im in enumerate(ims):
        x, y = (i % cols) * w, (i // cols) * (h + 14); sheet.paste(im, (x, y + 14)); d.text((x + 3, y + 1), f'{i * 0.25:.2f}s', fill='black')
    sheet.save(out / 'sheet.jpg', quality=82)
    g = [np.asarray(im.convert('L').resize((96, 72)), float) for im in ims]; dd = [float(np.abs(g[i] - g[i - 1]).mean()) for i in range(1, len(g))]
    med = float(np.median(dd)) if dd else 0
    json.dump({'step_seconds': 0.25, 'median_diff': round(med, 2), 'spikes': [{'t': round(i * 0.25, 2), 'diff': round(x, 1)} for i, x in enumerate(dd, 1) if x > 3 * med + 8]}, open(out / 'cuts.json', 'w'), indent=1)
    probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height,r_frame_rate:format=duration', '-of', 'json', str(clip)], capture_output=True, text=True).stdout)
    json.dump({'slug': a.slug, 'duration': float(probe['format']['duration']), 'stream': probe['streams'][0], 'sheet_frames': len(ims)}, open(out / 'clip.json', 'w'), indent=1)
    url = 'https://storage.googleapis.com/quickdraw_dataset/full/simplified/' + quote(S['category']) + '.ndjson'
    with urlopen(Request(url, headers={'Range': 'bytes=0-1500000'}), timeout=60) as r: rows = r.read().splitlines()[:-1]
    bank = []
    for line in rows:
        x = json.loads(line)
        if x['recognized'] and 4 <= len(x['drawing']) <= 20: bank.append({'key_id': str(x['key_id']), 'countrycode': x['countrycode'], 'drawing': x['drawing']})
        if len(bank) == 40: break
    json.dump({'category': S['category'], 'source_url': url, 'credit': 'Quick, Draw! contributors / Google Creative Lab, CC BY 4.0', 'drawings': bank}, open(out / 'doodles.json', 'w'))
    B = Image.new('RGB', (8 * 160, 5 * 172), 'white'); d = ImageDraw.Draw(B)
    for i, x in enumerate(bank):
        ox, oy = (i % 8) * 160, (i // 8) * 172; d.text((ox + 4, oy + 2), f'{i + 1}  {x["key_id"]}', fill=(90, 90, 90))
        for s in x['drawing']:
            pts = [(ox + 10 + u * 0.55, oy + 18 + v * 0.55) for u, v in zip(*s)]
            if len(pts) > 1: d.line(pts, fill='black', width=2)
    B.save(out / 'doodles.jpg', quality=85)
    clip.unlink(); import shutil; shutil.rmtree(out / 'f')
    print(a.slug, len(ims), 'sheet frames', len(bank), 'doodles', 'cuts', len(json.load(open(out / 'cuts.json'))['spikes']))


if __name__ == '__main__':
    main()
