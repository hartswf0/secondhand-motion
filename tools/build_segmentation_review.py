"""Build an offline source / SAM / cartoon inspector from pinned CI snapshots.

python tools/build_segmentation_review.py --cache /path/to/wave2-track-cache
Input snapshots must contain clip.json, track.json and frames/fNNN.jpg.
Model-reported IoU estimates are displayed as estimates, never source-fit measurements.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess

ROOT = Path(__file__).resolve().parent.parent
SUBJECTS = {
    'fan': ('Fan', 'The final CI sample crosses into the next cooking shot. It is retained for inspection and blocked from cartoon pairing.'),
    'tractor': ('Tractor', 'The masks combine the tractor with its trailer and sometimes the driver; they are not tractor-only outlines.'),
    'raccoon': ('Raccoon', 'The visible body is captured broadly. Hidden legs and the head turn still need direct source inspection.'),
    'pig': ('Pig', 'The mask follows the cropped pig. The drawing must keep the same crop.'),
    'mosquito': ('Mosquito', 'On skin. Thin legs and hairs can merge or disappear from the mask.'),
    'see-saw': ('See saw', 'This mask combines several boards. It cannot measure the fit of one selected board.'),
    'flying-saucer': ('Flying saucer', 'NASA CGI aeroshell. The drawing borrows its observed tilt, scale and crop.'),
    'rain': ('Rain', 'The model marks the wet demonstration road. Individual drops and splashes need separate observations.'),
    'hurricane': ('Storm surge', 'Water surges against a building. The mask switches to the building in one inspected sample.'),
    'tornado': ('Tornado', 'Some masks select sky or trees. They cannot establish the funnel boundary or rotation.'),
}


def build(cache):
    out = ROOT/'shots/wave2-segmentation'
    data = {}
    audit_file = ROOT/'tools/segmentation_audits.json'
    audits = json.loads(audit_file.read_text()) if audit_file.exists() else {}
    for slug, (title, note) in SUBJECTS.items():
        src = cache/slug
        if not (src/'track.json').is_file():
            continue
        target = out/'data'/slug
        target.mkdir(parents=True, exist_ok=True)
        clip = json.loads((src/'clip.json').read_text())
        track = json.loads((src/'track.json').read_text())
        assert len(track['frames']) == clip['n']
        for frame in track['frames']:
            assert sum(frame['rle']) == frame['W']*frame['H']
        for name in ['track.json', 'clip.json']:
            if (src/name).resolve() != (target/name).resolve():
                shutil.copy2(src/name, target/name)
        (target/'frames').mkdir(exist_ok=True)
        for f in range(clip['n']):
            name = f'f{f:03d}.jpg'
            if (src/'frames'/name).resolve() != (target/'frames'/name).resolve():
                shutil.copy2(src/'frames'/name, target/'frames'/name)
        ref = 'origin/wave2-track/'+slug
        track_hash = hashlib.sha256((src/'track.json').read_bytes()).hexdigest()
        prior = src/'provenance.json'
        if prior.exists():
            previous = json.loads(prior.read_text())
            assert previous['track_sha256'] == track_hash, 'Snapshot changed without updated provenance'
            sha = previous['commit']
        else:
            sha = subprocess.check_output(['git', 'rev-parse', ref], cwd=ROOT, text=True).strip()
            committed = subprocess.check_output(['git', 'show', ref+':track.json'], cwd=ROOT)
            assert hashlib.sha256(committed).hexdigest() == track_hash, 'Cache and branch disagree'
        assembly = ROOT/'shots'/slug/'integrated/shot.json'
        timeline = json.loads(assembly.read_text()) if assembly.exists() else {}
        times = [f['source_time'] for f in timeline.get('frames', [])]
        fit = timeline.get('mask_fit', {})
        fit_file = assembly.parent/'mask-fit.json'
        if not fit and fit_file.exists():
            fit = json.loads(fit_file.read_text())
        if not fit:
            checks = assembly.parent/'assembly-checks.json'
            fit = json.loads(checks.read_text()).get('mask_fit', {}) if checks.exists() else {}
        fit = {key: value for key, value in fit.items() if key != 'frames'} if isinstance(fit, dict) else {'status': str(fit)}
        provenance = {
            'branch': 'wave2-track/'+slug, 'commit': sha,
            'clip_id': clip['clip_id'], 'model': 'facebook/sam2.1-hiera-small',
            'time_basis': 'approximate clip-relative seconds from 12 fps resampling; paired to nearest recorded render source time, not exact decoded source PTS',
            'source_video_sha256': None,
            'source_video_note': 'CI did not retain the downloaded video hash or per-frame source PTS. Snapshot bytes are pinned; known shot mismatches are blocked by audit notes.',
            'detector': 'IDEA-Research/grounding-dino-tiny',
            'track_sha256': track_hash,
            'source_record': '../../../'+slug+'/source.json',
            'note': note,
        }
        audit = audits.get(slug, {})
        if audit.get('track_sha256') != track_hash:
            audit = {}
        (target/'audit.json').write_text(json.dumps(audit, indent=2)+'\n')
        (target/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
        data[slug] = dict(title=title, note=note, clip=clip, frames=track['frames'],
                          provenance=provenance, assembly_times=times,
                          assembly_fps=timeline.get('fps'), assembly_size=[timeline.get('W'), timeline.get('H')],
                          review_note=timeline.get('review_note', ''), drawing_fit=fit, audit=audit)
    template = (ROOT/'tools/templates/segmentation_review.html').read_text()
    html = template.replace('__DATA__', json.dumps(data, separators=(',', ':')).replace('</', '<\\/'))
    (out/'index.html').write_text(html)
    print(f'{out.relative_to(ROOT)}: {len(data)} subjects, {sum(d["clip"]["n"] for d in data.values())} sampled frames')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT/'shots/wave2-segmentation/data')
    build(parser.parse_args().cache)
