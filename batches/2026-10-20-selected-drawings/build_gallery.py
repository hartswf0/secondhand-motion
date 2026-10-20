#!/usr/bin/env python3
"""Reproduce the curated gallery from local assets; never selects or judges art."""
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
from io import BytesIO
from bisect import bisect_right
import argparse, base64, cv2, json, math, subprocess, os, tempfile

ROOT = Path(__file__).resolve().parent
DATASET = ROOT.parent / 'mia-quickdraw-dataset'
FPS = 12


def fit(im, size):
    return ImageOps.pad(im.convert('RGB'), size, method=Image.Resampling.LANCZOS, color='white')


def save_image(im, path):
    payload = BytesIO()
    im.save(payload, format='PNG')
    path = Path(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.part', delete=False) as f:
        temporary = Path(f.name)
        f.write(payload.getvalue())
        f.flush()
        os.fsync(f.fileno())
    temporary.replace(path)


def quadrants(path, size=(384, 288)):
    with Image.open(path) as im:
        w, h = im.size
        return [fit(im.crop((x*w//2, y*h//2, (x+1)*w//2, (y+1)*h//2)), size)
                for y in range(2) for x in range(2)]


def sheet(images, columns, size):
    out = Image.new('RGB', (columns*size[0], math.ceil(len(images)/columns)*size[1]), 'white')
    for i, im in enumerate(images):
        out.paste(fit(im, size), ((i % columns)*size[0], (i//columns)*size[1]))
    return out


def jpeg(im, size, quality):
    buf = BytesIO()
    fit(im, size).save(buf, format='JPEG', quality=quality, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def run(args, **kwargs):
    subprocess.run(args, check=True, **kwargs)


def assemble(item, skip_video=False):
    category = item['category']
    folder = ROOT / 'subjects' / category
    metadata = json.loads((folder/'source.json').read_text())
    source = metadata['source']
    times = [float(t) for t in metadata['key_times']]
    if len(times) != 4 or times != sorted(times):
        raise ValueError(f'{category}: expected four ordered key times')
    start, end = map(float, item['interval'])
    if not end > start:
        raise ValueError(f'{category}: empty interval')
    revision = item['selected_revision']
    art_path = folder / 'revisions' / f'keys-{revision}.png'
    art = quadrants(art_path)
    photos = quadrants(folder/'source-keys.png')
    for i, key in enumerate(art):
        save_image(key, folder/f'art-key-{i}.png')
    save_image(sheet(art, 2, (384, 288)), folder/'selected-keys.png')
    alternating = [im for pair in zip(photos, art) for im in pair]
    comparison = sheet(alternating, 2, (384, 288))
    save_image(comparison, folder/'key-comparison.png')
    excerpt = folder/'source-excerpt.mp4'
    comparison_video = folder/'held-key-comparison.mp4'
    original = DATASET/source['local_video_path']
    if not skip_video and original.exists():
        run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(start),
             '-i', str(original), '-t', str(end-start), '-vf', 'scale=384:288', '-r', str(FPS),
             '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '22', '-pix_fmt', 'yuv420p',
             '-movflags', '+faststart', str(excerpt)])
    if not excerpt.exists() and not original.exists():
        raise FileNotFoundError(f'{category}: source excerpt and original are both missing')
    # One sequential decode supplies both the held-key comparison and thumbnails.
    use_excerpt = excerpt.exists()
    cap = cv2.VideoCapture(str(excerpt if use_excerpt else original))
    if not cap.isOpened():
        raise RuntimeError(f'Cannot open video for {category}')
    input_fps = cap.get(cv2.CAP_PROP_FPS) or FPS
    if not use_excerpt:
        cap.set(cv2.CAP_PROP_POS_MSEC, start*1000)
    encoder = None
    if not skip_video:
        encoder = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
            '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', '768x288',
            '-framerate', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'fast',
            '-crf', '22', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(comparison_video)],
            stdin=subprocess.PIPE)
    thumbnails, thumb_times = [], []
    frame_index = 0
    next_thumb = 0.0
    try:
        while frame_index/input_fps < end-start-0.00001:
            ok, frame = cap.read()
            if not ok:
                break
            relative_time = frame_index/input_fps
            absolute_time = start+relative_time
            photo = fit(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), (384,288))
            key_index = max(0, min(3, bisect_right(times, absolute_time)-1))
            if encoder:
                combined = Image.new('RGB', (768,288), 'white')
                combined.paste(photo, (0,0)); combined.paste(art[key_index], (384,0))
                encoder.stdin.write(combined.tobytes())
            if relative_time+0.00001 >= next_thumb:
                thumbnails.append(photo.copy())
                thumb_times.append(round(absolute_time, 4))
                next_thumb += 1/6
            frame_index += 1
    finally:
        cap.release()
        if encoder:
            encoder.stdin.close()
            if encoder.wait() != 0:
                raise RuntimeError(f'ffmpeg failed for {category}')
    if not thumbnails:
        raise RuntimeError(f'{category}: no source frames decoded')
    review_path = item['review_path']
    review = json.loads((ROOT/review_path).read_text())
    prefix = f'subjects/{category}/'
    record = {
        'category': category, 'title': category.replace('_',' ').title(),
        'selected_revision': revision, 'interval': [start,end], 'duration': end-start,
        'key_times': times, 'fps': FPS, 'preview_fps': 6,
        'source_title': source.get('source_title',''), 'source': source,
        'key_bar': item['key_bar'], 'note': item.get('note',''),
        'review_path': review_path, 'review': review,
        'selection_scope': metadata.get('selection_scope',''),
        'review_scope': 'Still-key approvals only; no independent playback approval.',
        'rendering': 'Four held drawings switched at source key times; no interpolation or trained RL.',
        'paths': {'source_video':prefix+'source-excerpt.mp4',
                  'comparison_video':prefix+'held-key-comparison.mp4',
                  'source_grid':prefix+'source-keys.png', 'design':prefix+'design.png',
                  'art_grid':prefix+'selected-keys.png', 'comparison_grid':prefix+'key-comparison.png',
                  'revision':prefix+f'revisions/keys-{revision}.png'},
        'art_keys': [jpeg(im,(256,192),65) for im in art],
        'source_frames': [], 'source_frame_times': thumb_times,
    }
    return record, thumbnails


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-video', action='store_true', help='Reuse videos; rebuild gallery and preview payload only')
    args = parser.parse_args()
    manifest = json.loads((ROOT/'data/curation.json').read_text())
    built = [assemble(item,args.skip_video) for item in manifest['items']]
    records = [record for record, _ in built]
    payload = {'version':1, 'scope':'Source-backed held-key comparison; approvals cover still keys only.', 'items':records}
    # Keep the complete inline payload below the requested 900 kB budget.
    profiles = [((160,120),55), ((128,96),45), ((112,84),38), ((96,72),32), ((80,60),28)]
    for size, quality in profiles:
        for record, frames in built:
            record['source_frames'] = [jpeg(frame,size,quality) for frame in frames]
            record['source_thumbnail_size'] = list(size)
        encoded = json.dumps(payload,separators=(',',':'),ensure_ascii=False)
        if len(encoded.encode('utf-8')) < 900_000:
            break
    else:
        raise RuntimeError('Inline preview data exceeds 900 kB; shorten curated intervals')
    for record in records:
        (ROOT/'subjects'/record['category']/'preview-data.json').write_text(json.dumps(record,separators=(',',':'),ensure_ascii=False))
    (ROOT/'data/gallery-data.json').write_text(encoded)
    template = (ROOT/'gallery-template.html').read_text()
    # Escape script terminators in metadata while preserving valid JSON.
    (ROOT/'index.html').write_text(template.replace('/*GALLERY_DATA*/{}',encoded.replace('<','\\u003c')))
    print(f'Built {len(records)} subjects; inline preview data {len(encoded.encode("utf-8")):,} bytes.')


if __name__ == '__main__':
    main()
