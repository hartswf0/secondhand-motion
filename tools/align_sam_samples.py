"""Recover appearance correspondences between CI JPEGs and a retained source video.

This records an estimated correspondence, not the missing CI decode timestamps.
Only low-error, locally unique pixel matches are usable for inspector pairing.
Repeated frames, unknown source bytes and invalid segmentation remain separate concerns.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

import cv2
import numpy as np

MAX_GRAY_RMSE = 2.0
MIN_RUNNER_UP_GAP = 0.25
WINDOW_SECONDS = 0.25
SIZE = (96, 72)


def align(source, cache, output):
    clip = json.loads((cache/'clip.json').read_text())
    cap = cv2.VideoCapture(str(source))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ok, image = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        frames.append(cv2.resize(gray, SIZE, interpolation=cv2.INTER_AREA).astype(np.float32))
    cap.release()
    assert frames and fps > 0, 'Source video could not be decoded'
    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'frame=best_effort_timestamp_time', '-of', 'json', str(source)], text=True))
    times = [float(f['best_effort_timestamp_time']) for f in probe.get('frames', [])
             if 'best_effort_timestamp_time' in f]
    clock = 'decoded best_effort_timestamp_time'
    if len(times) != len(frames):
        times = [i/fps for i in range(len(frames))]
        clock = 'frame index / reported fps; decoded timestamps unavailable'
    samples = []
    radius = max(2, int(np.ceil(WINDOW_SECONDS*fps)))
    for i in range(clip['n']):
        path = cache/'frames'/f'f{i:03d}.jpg'
        image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        assert image is not None, f'Missing sample {path}'
        small = cv2.resize(image, SIZE, interpolation=cv2.INTER_AREA).astype(np.float32)
        nominal = clip['t0']+i/clip['fps']
        center = min(range(len(times)), key=lambda j: abs(times[j]-nominal))
        indices = range(max(0, center-radius), min(len(frames), center+radius+1))
        errors = sorted((float(np.sqrt(np.mean((small-frames[j])**2))), j) for j in indices)
        rmse, index = errors[0]
        runner_up = errors[1][0] if len(errors) > 1 else rmse
        usable = rmse <= MAX_GRAY_RMSE and runner_up-rmse >= MIN_RUNNER_UP_GAP
        samples.append(dict(sample=i, nominal_time=round(nominal, 8),
                            matched_source_index=index, matched_source_time=times[index],
                            gray_rmse=round(rmse, 6), runner_up_rmse=round(runner_up, 6),
                            usable_for_pairing=bool(usable),
                            sample_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    usable_times = [r['matched_source_time'] for r in samples if r['usable_for_pairing']]
    assert all(a <= b for a, b in zip(usable_times, usable_times[1:])), 'Appearance matches reverse source order'
    result = dict(method='Local pixel matching after grayscale area resize to 96x72; no model inference',
                  scope='Estimated appearance correspondences to the retained raw video. Original CI input hash and decode PTS were not recorded; this does not recover them or validate masks, drawing quality, recognition or playback.',
                  clip_id=clip['clip_id'], comparison_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  track_sha256=hashlib.sha256((cache/'track.json').read_bytes()).hexdigest(),
                  source_clock=clock, source_fps=fps,
                  thresholds=dict(max_gray_rmse=MAX_GRAY_RMSE, min_runner_up_rmse_gap=MIN_RUNNER_UP_GAP,
                                  candidate_radius_seconds=WINDOW_SECONDS, grayscale_size=list(SIZE)),
                  usable_samples=sum(r['usable_for_pairing'] for r in samples), samples=samples)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = align(args.source, args.cache, args.output)
    print(f'{report["usable_samples"]}/{len(report["samples"])} samples have usable appearance correspondences')
