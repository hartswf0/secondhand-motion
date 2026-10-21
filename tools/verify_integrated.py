"""Check integrated movie artifacts against their saved keys, without judging motion.

Usage: python tools/verify_integrated.py monkey ant tiger
Run after the builders have frozen their files. Output is a technical report;
it does not establish source-pose, recognition, playback or training approval.
"""
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PIXEL_MAE_LIMIT = 2.0


def strict_json(path):
    def invalid(value):
        raise ValueError(f'{path}: non-finite JSON constant {value}')
    return json.loads(path.read_text(), parse_constant=invalid)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        self.urls.extend(v for k, v in attrs if k in ('href', 'src', 'poster') and v)


def verify_movie(args):
    path, count, fps, keys, base, comparison = args
    captured = {}
    cap = cv2.VideoCapture(str(path))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    n = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if n in keys:
            captured[n] = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        n += 1
    cap.release()
    assert n == count, f'{path}: decoded {n}, expected {count}'
    assert abs(actual_fps-fps) < 1e-6, f'{path}: fps {actual_fps}, expected {fps}'
    decoded = subprocess.run(
        ['ffmpeg', '-v', 'error', '-xerror', '-threads', '1', '-i', str(path), '-f', 'null', '-'],
        capture_output=True, text=True)
    assert decoded.returncode == 0, f'{path}: {decoded.stderr}'
    differences = []
    for ordinal, index in enumerate(keys, 1):
        expected = np.asarray(Image.open(base/f'key-{ordinal:02d}.png').convert('RGB'))
        actual = captured[index]
        if comparison:
            h, w = expected.shape[:2]
            header = actual.shape[0]-h
            assert actual.shape[1] == 2*w and 0 <= header <= 64, f'{path}: unsupported comparison layout'
            actual = actual[header:, w:]
        assert actual.shape == expected.shape, f'{path}: key image dimensions differ'
        mae = float(np.mean(np.abs(actual.astype(np.float32)-expected.astype(np.float32))))
        assert mae < PIXEL_MAE_LIMIT, f'{path}: key {ordinal} frame {index} RGB MAE {mae:.4f}'
        differences.append(dict(key=ordinal, frame=index, rgb_mae=round(mae, 6)))
    return dict(path=str(path.relative_to(ROOT)), decoded_frames=n, fps=actual_fps,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(), key_pixel_checks=differences)


def verify(slug):
    folder = ROOT/'shots'/slug
    base = folder/'integrated'
    assert base.is_dir(), f'{slug}: no integrated assembly'
    assert not list(base.rglob('*.tmp.mp4')), f'{slug}: temporary movies remain'
    assert not [p for p in base.rglob('*') if p.is_dir() and p.name.startswith('.') and 'render' in p.name], f'{slug}: temporary render directory remains'
    shot = strict_json(base/'shot.json')
    count, fps, keys = shot['frame_count'], shot['fps'], shot['keys']
    assert count > 0 and fps > 0 and keys, f'{slug}: empty timeline'
    assert all(isinstance(k, int) and 0 <= k < count for k in keys)
    assert keys == sorted(set(keys)), f'{slug}: repeated or unordered keys'
    frames = shot['frames']
    assert len(frames) == count
    times = [f['source_time'] for f in frames]
    assert all(isinstance(t, (int, float)) and np.isfinite(t) for t in times)
    assert all(a <= b for a, b in zip(times, times[1:])), f'{slug}: source clock goes backward'
    json_files = list(base.rglob('*.json')) + [folder/'tests.json']
    for path in json_files:
        strict_json(path)
    html = (base/'index.html').read_text()
    parser = Links()
    parser.feed(html)
    local_links = 0
    for url in parser.urls:
        if url.startswith(('http:', 'https:', '#', 'data:', 'mailto:')):
            continue
        path = url.split('#', 1)[0].split('?', 1)[0]
        assert (base/path).exists(), f'{slug}: broken relative URL {url}'
        local_links += 1
    for attrs, code in re.findall(r'<script\b([^>]*)>(.*?)</script>', html, re.S):
        if re.search(r'type=["\']application/(?:ld\+)?json["\']', attrs):
            continue
        checked = subprocess.run(['node', '-e', 'new Function('+json.dumps(code)+')'],
                                 capture_output=True, text=True)
        assert checked.returncode == 0, f'{slug}: inline script syntax {checked.stderr}'
    module_path = ROOT/'batches/2026-10-20-selected-drawings/loop.py'
    spec = importlib.util.spec_from_file_location('repair_ledger', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with (folder/'ledger.jsonl').open() as handle:
        ledger = module.read_ledger(handle)
    movie_args = [(base/'cartoon.mp4', count, fps, keys, base, False),
                  (base/'source-excerpt.mp4', count, fps, [], base, False),
                  (base/'comparison.mp4', count, fps, keys, base, True)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        movies = list(pool.map(verify_movie, movie_args))
    return dict(subject=slug, technical_pass=True, frames=count, fps=fps, keys=len(keys),
                strict_json_files=len(json_files), relative_links=local_links,
                hash_verified_ledger_entries=len(ledger), movies=movies,
                scope='Artifact integrity and saved-key/movie agreement only; no artistic, recognition, normal-speed motion or training approval inferred.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('subjects', nargs='+')
    args = parser.parse_args()
    print(json.dumps([verify(slug) for slug in args.subjects], indent=2, allow_nan=False))
