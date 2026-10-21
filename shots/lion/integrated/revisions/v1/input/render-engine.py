"""Render a source-paired, editable integrated review from frozen native vectors.

Examples:
  python tools/integrated_batch.py --snapshot frog
  python tools/integrated_batch.py --subject frog --config shots/frog/integrated/config.json --source /path/raw.mp4

Snapshot only copies inputs and proposes a config. A builder must inspect source
continuity, construction compatibility, key beats and every optional extra before
rendering. This tool does not confer artistic, recognition or playback approval.
Config paths are relative to the config file. GWP cast is screen-space; scenery
is held world geometry shifted separately by camera * z_ref / plane depth.
"""
from pathlib import Path
import argparse
import hashlib
import html
import importlib.util
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

import cairosvg
import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
cv2.setNumThreads(1)
PAPER = '#fffdf7'
INK = '#29261f'


def read(path):
    def reject(value):
        raise ValueError(f'Non-finite JSON constant {value}: {path}')
    return json.loads(Path(path).read_text(), parse_constant=reject)


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_source(path):
    record = read(path)
    return record.get('source', record)


def snapshot(subject):
    """Freeze existing inputs without changing a GWP/drawn source or approval."""
    folder = ROOT/'shots'/subject
    out = folder/'integrated'
    inputs = out/'input'
    inputs.mkdir(parents=True, exist_ok=True)
    assert not (out/'config.json').exists(), 'Config already exists; snapshot never overwrites it'
    gwp = ROOT/'shots'/f'{subject}-gwp'
    for origin, target in [(gwp/'shot.json', 'gwp-shot.json'),
                           (gwp/'clip.json', 'clip.json'),
                           (folder/'design.json', 'design.json'),
                           (folder/'source.json', 'source.json')]:
        shutil.copy2(origin, inputs/target)
    if (folder/'design.png').exists():
        shutil.copy2(folder/'design.png', inputs/'design.png')
    sp = ROOT/'rigs'/f'{subject.replace("-", "_")}_spec.json'
    if sp.exists():
        shutil.copy2(sp, inputs/'rig-spec.json')
    if (folder/'drawn').exists():
        (inputs/'drawn').mkdir(exist_ok=True)
        for p in sorted((folder/'drawn').glob('*.json')):
            shutil.copy2(p, inputs/'drawn'/p.name)
    clip, shot = read(inputs/'clip.json'), read(inputs/'gwp-shot.json')
    t0 = clip['t0']
    interval = [t0, t0+(len(shot['cast']['frames'])-1)/clip['fps']]
    config = dict(title=subject.replace('-', ' ').capitalize(), interval=interval,
                  W=shot['W'], H=shot['H'], design='input/design.json',
                  source_record='input/source.json', gwp_snapshot='input/gwp-shot.json',
                  clip_snapshot='input/clip.json', source_sha256=None,
                  key_times=[t0+k/clip['fps'] for k in shot['cast']['keys']],
                  extra_strokes=[], fill_strokes=[], background_fill=False,
                  continuous_source={'pass': None, 'evidence': 'Builder inspection required'},
                  compatibility={'status': 'not yet inspected'}, verified_contacts=[],
                  review_note='Source, native identity and pose review pending. Normal-speed playback and classifier unrun.',
                  assembly_summary='Frozen native vector study, paired with the retained raw source.')
    write(out/'config.json', config)
    print(f'{subject}: inputs frozen; inspect and complete {out.relative_to(ROOT)}/config.json before rendering')


def strokes(value):
    result = [np.asarray(s, dtype=float) for s in value]
    assert result and all(s.ndim == 2 and s.shape[1] == 2 and len(s) > 0 and np.isfinite(s).all() for s in result), 'Invalid stroke arrays'
    return result


def mix_strokes(a, b, t, native_n=None):
    if t <= 1e-9:
        return [s.copy() for s in a]
    if t >= 1-1e-9:
        return [s.copy() for s in b]
    n = native_n if native_n is not None else len(a)
    assert len(a) >= n and len(b) >= n and all(a[i].shape == b[i].shape for i in range(n)), 'Native topology changes between samples; no unmatched morph permitted'
    result = [(1-t)*a[i]+t*b[i] for i in range(n)]
    if native_n is not None:
        chosen = a if t < .5 else b
        for i in range(n, len(chosen)):
            result.append((1-t)*a[i]+t*b[i] if i < min(len(a), len(b)) and a[i].shape == b[i].shape else chosen[i].copy())
    else:
        assert len(a) == len(b), 'Scene topology changed without an exposure rule'
    return result


def between(times, time):
    assert times and times[0]-1e-5 <= time <= times[-1]+1e-5, f'Time {time} outside vector observation coverage [{times[0]}, {times[-1]}]'
    b = min(int(np.searchsorted(times, time)), len(times)-1)
    a = max(0, b-1)
    fraction = 0.0 if times[b] == times[a] else (time-times[a])/(times[b]-times[a])
    return a, b, float(np.clip(fraction, 0, 1))


def native_design(config, base):
    design = read(base/config['design'])
    assert 'key_id' in design and 'drawing' in design, 'Lock a real Quick, Draw! record'
    return design, [len(s[0]) for s in design['drawing']]


def decode_source(path):
    cap = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ok, image = cap.read()
        if not ok:
            break
        frames.append(image)
    cap.release()
    assert frames and fps > 0, 'Source video did not decode'
    probe = read_probe(path, frames=True)
    times = [float(f['best_effort_timestamp_time']) for f in probe.get('frames', []) if 'best_effort_timestamp_time' in f]
    clock = 'decoded best_effort_timestamp_time'
    if len(times) != len(frames):
        times = [i/fps for i in range(len(frames))]
        clock = 'source index / reported fps (decoded PTS unavailable)'
    assert all(a <= b for a, b in zip(times, times[1:])), 'Source PTS goes backwards'
    return frames, times, fps, clock


def read_probe(path, frames=False):
    entries = 'frame=best_effort_timestamp_time' if frames else 'stream=nb_read_frames,r_frame_rate,width,height'
    args = ['ffprobe', '-v', 'error', '-select_streams', 'v:0']
    if not frames:
        args += ['-count_frames']
    return json.loads(subprocess.check_output(args+['-show_entries', entries, '-of', 'json', str(path)], text=True))


def nearest_index(times, time):
    b = min(int(np.searchsorted(times, time)), len(times)-1)
    a = max(0, b-1)
    return a if abs(times[a]-time) <= abs(times[b]-time) else b


def contain(image, W, H):
    image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    scale = min(W/image.width, H/image.height)
    image = image.resize((round(image.width*scale), round(image.height*scale)), Image.Resampling.LANCZOS)
    result = Image.new('RGB', (W, H), PAPER)
    result.paste(image, ((W-image.width)//2, (H-image.height)//2))
    return result


def points(value):
    return ' '.join(f'{x:.4f},{y:.4f}' for x, y in value)


def polyline(value, width=1.5, color=INK, fill=None):
    if len(value) < 2:
        x, y = value[0]
        return f'<circle cx="{x:.4f}" cy="{y:.4f}" r="{width/2:.3f}" fill="{color}"/>'
    if fill:
        return f'<polygon points="{points(value)}" fill="{fill}" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>'
    return f'<polyline points="{points(value)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'


def render_svg(W, H, character, scenery, config, character_only=False):
    content = f'<rect width="{W}" height="{H}" fill="{PAPER}"/>'
    if not character_only:
        for o in scenery:
            for s in o['strokes']:
                filled = None
                if config.get('background_fill') and len(s) > 2:
                    span = max(np.ptp(s[:, 0]), np.ptp(s[:, 1]), 1)
                    if np.linalg.norm(s[0]-s[-1]) < .12*span:
                        filled = PAPER
                content += polyline(s, config.get('background_width', 1.0), '#aba28f', filled)
    for i in (config.get('fill_strokes', []) if character else []):
        assert 0 <= i < len(character), 'Fill index outside native character'
        content += f'<polygon points="{points(character[i])}" fill="{PAPER}"/>'
    content += ''.join(polyline(s, config.get('stroke_width', 1.65)) for s in character)
    crop = config.get('crop', [0, 0, W, H])
    view = f'{crop[0]} {crop[1]} {crop[2]-crop[0]} {crop[3]-crop[1]}'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="{view}">{content}</svg>'


def png(svg):
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGB')


def vector_inputs(config, base):
    """Return timestamped immutable observations and held/background metadata."""
    if config.get('gwp_snapshot'):
        shot, clip = read(base/config['gwp_snapshot']), read(base/config['clip_snapshot'])
        observations = [strokes(value) for value in shot['cast']['frames']]
        times = config.get('observation_times', [clip['t0']+i/clip['fps'] for i in range(len(observations))])
        times = [float(t) for t in times]
        assert len(times) == len(observations), 'observation_times must cover every frozen cast frame'
        camera = np.asarray(shot.get('camera', [[0, 0]]*len(times)), float)
        assert camera.shape == (len(times), 2)
        key_times = config.get('key_times', [times[k] for k in shot['cast']['keys']])
        notes = {round(times[row['f']], 7): row.get('note', '') for row in shot.get('xsheet', [])}
        planes = shot.get('planes', [])
        objects = shot.get('objects', [])
        return observations, times, camera, key_times, notes, planes, objects, shot.get('z_ref', 2), shot.get('camera_source', '')
    keys = config['keys']
    observations, times, notes = [], [], {}
    for row in keys:
        value = read(base/row['file']) if row.get('file') else row
        observations.append(strokes(value['strokes']))
        times.append(float(row['time']))
        notes[round(times[-1], 7)] = row.get('note', value.get('why', ''))
    background = config.get('background', {})
    camera = np.asarray(config.get('camera', [[0, 0]]*len(times)), float)
    return observations, times, camera, times, notes, background.get('planes', []), background.get('objects', []), background.get('z_ref', 2), config.get('camera_note', '')


def scenery_at(objects, planes, camera, index_a, index_b, fraction, z_ref):
    depths = {p['id']: p.get('z', z_ref) for p in planes}
    result = []
    for o in objects:
        if o.get('frames'):
            A, B = o['frames'][index_a], o['frames'][index_b]
            if not A or not B:
                chosen = A if fraction < .5 else B
                value = strokes(chosen) if chosen else []
            else:
                aa, bb = strokes(A), strokes(B)
                same = len(aa) == len(bb) and all(x.shape == y.shape for x, y in zip(aa, bb))
                value = mix_strokes(aa, bb, fraction) if same else (aa if fraction < .5 else bb)
        else:
            value = strokes(o['strokes']) if o.get('strokes') else []
        # GWP cast is already in source screen coordinates; all scene objects,
        # including secondary cast, retain their own world/depth camera shift.
        shift = np.zeros(2) if o.get('coordinate_space') == 'screen' else camera*(z_ref/depths.get(o.get('plane'), z_ref))
        result.append(dict(id=o['id'], source=o.get('source', ''), plane=o.get('plane'),
                           dynamic=bool(o.get('frames')), strokes=[s+shift for s in value]))
    return result


def contact_sheets(out, keys, source_frames, source_times, W, H):
    tw = min(240, W)
    th = round(H*tw/W)
    rows_per_sheet = 3
    for group_start in range(0, len(keys), 6):
        selected = keys[group_start:group_start+6]
        sheet = Image.new('RGB', (4*tw, math.ceil(len(selected)/2)*(th+24)), '#f5f1e8')
        draw = ImageDraw.Draw(sheet)
        for j, (ordinal, f) in enumerate(selected, group_start+1):
            x, y = ((j-group_start-1)%2)*2*tw, ((j-group_start-1)//2)*(th+24)
            photo = Image.open(out/f'source-{ordinal:02d}.jpg').resize((tw, th))
            drawing = Image.open(out/f'key-{ordinal:02d}.png').resize((tw, th))
            sheet.paste(photo, (x, y+24)); sheet.paste(drawing, (x+tw, y+24))
            draw.text((x+5, y+5), f'KEY {ordinal} | {source_times[f]:.3f}s', fill=INK)
        sheet.save(out/f'paired-keys-{group_start//6+1:02d}.jpg', quality=94)
    sampled = np.linspace(0, len(source_frames)-1, 16).round().astype(int)
    sheet = Image.new('RGB', (4*tw, 4*(th+24)), '#f5f1e8')
    draw = ImageDraw.Draw(sheet)
    for j, f in enumerate(sampled):
        x, y = (j%4)*tw, (j//4)*(th+24)
        sheet.paste(source_frames[f].resize((tw, th)), (x, y+24))
        draw.text((x+5, y+5), f'{source_times[f]:.3f}s', fill=INK)
    sheet.save(out/'source-contact-sheet.jpg', quality=94)


def trace_keys(out, count, W, H):
    sys.path.insert(0, str(ROOT/'tools'))
    import trace_keys as tracer
    rows = []
    for k in range(1, count+1):
        image = Image.open(out/f'character-key-{k:02d}.png')
        lines, ink, half_width = tracer.trace(image)
        recall, precision, parts = tracer.score(lines, ink, W, H, half_width)
        rows.append(dict(key=k, strokes=lines, recall=recall, precision=precision, parts_kept=parts))
    write(out/'traced.json', {'integrated': {'W': W, 'H': H, 'keys': rows}})
    return dict(min_recall=min(r['recall'] for r in rows), min_parts_kept=min(r['parts_kept'] for r in rows),
                keys=count, **{'pass': all(r['recall'] >= .98 and r['parts_kept'] == 1 for r in rows)})


def build_page(out, shot, config):
    escape = html.escape
    pairs = sorted(out.glob('paired-keys-*.jpg'))
    assets = ''.join(f'<figure><img src="{p.name}" alt="Source and drawing key pairs" loading="lazy"></figure>' for p in pairs)
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    page += f'<title>{escape(shot["title"])} · Secondhand Motion</title><link rel="icon" href="../../../favicon.svg">'
    page += '<style>*{box-sizing:border-box}body{margin:0;background:#f5f1e8;color:#29261f;font:17px/1.5 system-ui}main{max-width:1100px;margin:auto;padding:20px}nav{display:flex;gap:20px;flex-wrap:wrap}a{color:inherit}h1{font-size:clamp(30px,7vw,56px);line-height:1.1}video,img{display:block;width:100%;height:auto}figure{margin:20px 0}button{font:inherit;padding:9px 16px;margin:4px;border:1px solid #aaa08f;border-radius:5px;background:#fffdf7;color:#29261f}.note{padding:14px;border-left:4px solid #ba702e;background:#fffdf7}.controls{display:flex;gap:8px;flex-wrap:wrap}.meta{font-size:14px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}</style><main>'
    page += '<nav><a href="../../../index.html">Secondhand Motion</a><a href="../../moving-drawings.html">All moving drawings</a><a href="source.json">Source record</a><a href="shot.json">Editable timeline</a><a href="assembly-checks.json">Checks</a></nav>'
    page += f'<h1>{escape(shot["title"])}</h1><p>{escape(shot["assembly_summary"])}</p><p class="note">{escape(shot["review_note"])}</p>'
    page += f'<p class="meta">{len(shot["keys"])} paired keys · {shot["frame_count"]} frames · {shot["fps"]} fps. Native Quick, Draw! key {escape(str(shot["design"]["key_id"]))}.</p>'
    page += '<div class="controls"><button data-mode="comparison">Together</button><button data-mode="cartoon">Drawing</button><button data-mode="source-excerpt">Footage</button></div><video id="movie" controls playsinline preload="metadata" src="comparison.mp4" poster="comparison-poster.jpg"></video>'
    page += '<h2>Source and keyframe checks</h2>'+assets+'<details><summary>Source interval</summary><img src="source-contact-sheet.jpg" alt="Sixteen sampled retained source frames"><a href="compatibility.json">Construction compatibility</a></details>'
    page += '<details><summary>Original locked drawing</summary><img src="design.png" alt="Original locked Quick, Draw! design"><a href="design.json">Native record</a></details>'
    page += '<p class="meta">Quick, Draw! contributors / Google Creative Lab, CC BY 4.0. Archive reported rights remain in source.json. Review candidate; no training ran.</p></main>'
    page += "<script>const v=document.querySelector('#movie');let resume=0,playing=false;v.addEventListener('loadedmetadata',()=>{v.currentTime=Math.min(resume,Math.max(0,v.duration-.001));if(playing)v.play().catch(()=>{});});document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>{resume=v.currentTime;playing=!v.paused;v.pause();v.src=b.dataset.mode+'.mp4';v.poster=b.dataset.mode==='comparison'?'comparison-poster.jpg':b.dataset.mode==='cartoon'?'poster.png':'source-01.jpg';}));</script></html>"
    (out/'index.html').write_text(page)


def refresh_page(config_path, output=None):
    config_path = Path(config_path).resolve()
    config = read(config_path)
    out = Path(output).resolve() if output else config_path.parent
    shot = read(out/'shot.json')
    for field in ['review_note', 'assembly_summary', 'revision', 'review_status']:
        if field in config:
            shot[field] = config[field]
    # A page refresh cannot grant playback or training acceptance.
    shot['motion_approved'] = False
    shot['train_eligible'] = False
    shot['training_ran'] = False
    write(out/'shot.json', shot)
    build_page(out, shot, config)
    print(f'{out}: page and review metadata refreshed, media unchanged')


def build(subject, config_path, source, output=None):
    config_path = Path(config_path).resolve()
    base = config_path.parent
    config = read(config_path)
    out = Path(output).resolve() if output else base
    out.mkdir(parents=True, exist_ok=True)
    expected_sha = config.get('source_sha256')
    assert expected_sha and expected_sha == sha(source), 'Set source_sha256 to the retained raw source hash; mismatched source bytes refused'
    W, H, fps = int(config['W']), int(config['H']), 24
    assert W > 0 and H > 0 and W%2 == 0 and H%2 == 0
    start, end = map(float, config['interval'])
    assert end > start
    design, native_counts = native_design(config, base)
    observations, observation_times, cameras, chosen_times, notes, planes, objects, z_ref, camera_source = vector_inputs(config, base)
    assert all(a < b for a, b in zip(observation_times, observation_times[1:])), 'Observation times must increase'
    assert len(cameras) == len(observation_times)
    count = int(math.ceil((end-start)*fps-1e-8))+1
    source_times = [min(start+f/fps, end) for f in range(count)]
    key_frames = sorted(set([0, count-1]+[min(range(count), key=lambda f: abs(source_times[f]-float(t))) for t in chosen_times if start-1e-6 <= float(t) <= end+1e-6]))
    assert len(key_frames) >= 2
    native_n = len(native_counts)
    extra_indices = {int(o['index']) for o in config.get('extra_strokes', [])}
    first_count = max(len(fr) for fr in observations)
    assert all(len(fr) >= native_n for fr in observations)
    assert set(range(native_n, first_count)) <= extra_indices, 'Every extra stroke needs explicit index/source/note provenance in extra_strokes'
    for extra in config.get('extra_strokes', []):
        assert extra.get('source') and extra.get('note'), 'Extra-stroke provenance incomplete'
    topology = all(all(len(fr[i]) == native_counts[i] for i in range(native_n)) for fr in observations)
    native_note = 'Native first-stroke IDs and point counts retained' if topology else 'Native first-stroke IDs or point counts differ; topology gate fails, no silent resampling performed'
    raw, pts, raw_fps, clock = decode_source(source)
    assert start >= pts[0]-.1 and end <= pts[-1]+1/raw_fps+.001, 'Retained interval exceeds decoded source coverage'
    record = load_source(base/config['source_record']).copy()
    record.update(start_seconds=start, end_seconds=end, interval_seconds=[start, end],
                  source_sha256=expected_sha, time_basis='clip_relative_seconds', source_clock=clock,
                  source_approved=False, motion_approved=False, train_eligible=False,
                  source_selection=config.get('continuous_source', {'pass': None, 'evidence': 'Not recorded'}),
                  vector_observation_clock=config.get('observation_time_note', 'Nominal CI resampling clock; original CI source PTS/input hash unavailable'))
    write(out/'source.json', record)
    write(out/'design.json', design)
    # Design sheet uses precisely the locked record, never a posed key.
    native = strokes([list(zip(s[0], s[1])) for s in design['drawing']])
    design_svg = render_svg(320, 320, [(s+24)*.95 for s in native], [], {'stroke_width': 2}, True)
    png(design_svg).save(out/'design.png')
    compatibility = config.get('compatibility', {}).copy()
    compatibility.update(native_key_id=design['key_id'], native_strokes=native_n, original_point_counts=native_counts,
                         native_topology=topology, topology_note=native_note, extras=config.get('extra_strokes', []))
    write(out/'compatibility.json', compatibility)
    frames, photos = [], []
    xsheet, camera_rows = [], []
    with tempfile.TemporaryDirectory(prefix=f'secondhand-motion-{subject}-') as td:
        temp = Path(td)
        for f, time in enumerate(source_times):
            a, b, fraction = between(observation_times, time)
            character = mix_strokes(observations[a], observations[b], fraction, native_n)
            camera = (1-fraction)*cameras[a]+fraction*cameras[b]
            scenery = scenery_at(objects, planes, camera, a, b, fraction, z_ref)
            svg = render_svg(W, H, character, scenery, config)
            drawing = png(svg)
            index = nearest_index(pts, time)
            photo = contain(raw[index], W, H)
            if config.get('crop'):
                x0, y0, x1, y1 = map(float, config['crop'])
                assert 0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H and abs((x1-x0)/(y1-y0)-W/H) < 1e-6, 'Common crop must be inside the source and preserve output aspect'
                photo = photo.crop((x0, y0, x1, y1)).resize((W, H), Image.Resampling.LANCZOS)
            photos.append(photo)
            pair = Image.new('RGB', (2*W, H+24), '#f5f1e8')
            pair.paste(photo, (0, 24)); pair.paste(drawing, (W, 24))
            pen = ImageDraw.Draw(pair)
            pen.text((8, 6), f'ARCHIVE | requested {time:.3f}s / decoded {pts[index]:.3f}s', fill=INK)
            pen.text((W+8, 6), 'NATIVE DRAWING | review candidate', fill=INK)
            drawing.save(temp/f'cartoon-{f:04d}.ppm'); photo.save(temp/f'source-{f:04d}.ppm'); pair.save(temp/f'pair-{f:04d}.ppm')
            cast_objects = [dict(id=subject, source_key_id=design['key_id'], strokes=[s.round(4).tolist() for s in character])]
            frames.append(dict(f=f, time=f/fps, source_time=time, source_frame_index=index, source_index_time=pts[index], camera=camera.tolist(), objects=cast_objects))
            camera_rows.append(camera.tolist())
            note_time = min(notes, key=lambda t: abs(t-time)) if notes else None
            note = notes.get(note_time, '') if note_time is not None else ''
            key_notes = config.get('key_notes', {})
            if key_notes:
                ntime = min(key_notes, key=lambda k: abs(float(k)-time))
                if abs(float(ntime)-time) <= 1/fps: note = key_notes[ntime]
            xsheet.append(dict(f=f, kind='K' if f in key_frames else 'I', note=note or ('Observed native-vector key' if f in key_frames else 'Linear correspondence between frozen source-observed vector samples; not an inferred contact solve')))
            if f in key_frames:
                k = key_frames.index(f)+1
                drawing.save(out/f'key-{k:02d}.png'); (out/f'key-{k:02d}.svg').write_text(svg)
                ch = render_svg(W, H, character, [], config, True)
                (out/f'character-key-{k:02d}.svg').write_text(ch); png(ch).save(out/f'character-key-{k:02d}.png')
                photo.save(out/f'source-{k:02d}.jpg', quality=94)
            if f == 0:
                drawing.save(out/'poster.png'); pair.save(out/'comparison-poster.jpg', quality=94)
                bg = render_svg(W, H, [], scenery, config)
                (out/'background.svg').write_text(bg); png(bg).save(out/'background.png')
        validation = {}
        for pattern, name in [('cartoon', 'cartoon.mp4'), ('source', 'source-excerpt.mp4'), ('pair', 'comparison.mp4')]:
            target = temp/name
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(fps), '-i', str(temp/(pattern+'-%04d.ppm')), '-an', '-c:v', 'libx264', '-threads', '1', '-preset', 'fast', '-crf', '12', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target)], check=True)
            subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-threads', '1', '-i', str(target), '-f', 'null', '-'], check=True)
            info = read_probe(target)['streams'][0]
            assert int(info['nb_read_frames']) == count
            os.replace(target, out/name)
            validation[name] = dict(decoded_frames=count, fps=fps, complete=True, sha256=sha(out/name))
    trace = trace_keys(out, len(key_frames), W, H)
    held = True  # Static scene geometry is held; separately credited animated operations are not background regeneration.
    animated_scene_ids = [o['id'] for o in objects if o.get('frames')]
    checks = dict(rendered_frames=count, keys=len(key_frames), full_decode=True,
                  source_sha256_verified=True, native_topology=topology,
                  trace_fidelity=trace, held_background_geometry=held,
                  background_strokes_unchanged_fraction=1.0 if held else None,
                  mask_fit={'pass': False, 'status': 'not measured by this assembly', 'reason': 'No audited same-instance mask target evaluated against this final native render'},
                  recognition='not run', independent_playback='not run',
                  verified_planted_intervals=len(config.get('verified_contacts', [])),
                  foot_slide_gate=False, release_approved=False, training_ran=False,
                  source_aspect_preserved=True, source_clock=clock, common_source_drawing_crop=config.get('crop'),
                  animated_scene_objects=animated_scene_ids, background_gate_scope='Static scene objects only; separately credited animated props/operators retain their explicit exposure sequences')
    summary = config.get('assembly_summary', 'Frozen native vectors paired with the retained archive source.')
    review_note = config.get('review_note', 'Identity and source pose review pending; classifier and normal-speed playback unrun.')
    shot = dict(title=config['title'], revision=config.get('revision', 'integrated-v1'),
                status='assembled_candidate_review_pending', W=W, H=H, fps=fps,
                frame_count=count, duration=count/fps, keys=key_frames,
                source=record, design=design, frames=frames, xsheet=xsheet,
                camera={'source': camera_source, 'note': config.get('camera_note', ''), 'samples': camera_rows},
                planes=planes, scene_objects=objects, z_ref=z_ref, viewport_crop=config.get('crop'),
                vector_observation_clock=config.get('observation_time_note', 'Nominal CI resampling clock; original CI source PTS/input hash unavailable'),
                assembly_summary=summary, review_note=review_note,
                training_ran=False, motion_approved=False, train_eligible=False)
    write(out/'shot.json', shot); write(out/'assembly-checks.json', checks); write(out/'video-validation.json', validation)
    write(out/'correspondence.json', dict(native_key_id=design['key_id'], original_point_counts=native_counts, native_topology=topology,
                                        observations=observation_times, key_source_times=[source_times[k] for k in key_frames],
                                        interpolation='linear same-stroke/point correspondence between frozen observations; no procedural gait',
                                        verified_contacts=config.get('verified_contacts', [])))
    contact_sheets(out, list(enumerate(key_frames, 1)), photos, source_times, W, H)
    build_page(out, shot, config)
    (out/'README.md').write_text(f'# {config["title"]}\n\n{summary}\n\n{review_note}\n\nReproduce with `python tools/integrated_batch.py --subject {subject} --config shots/{subject}/integrated/config.json --source /path/to/raw.mp4`. Inputs are frozen under input/ and the source hash is pinned. The raw source remains external.\n\nNative topology: {topology}. {native_note}. Extra strokes are explicitly credited in compatibility.json. Camera/scenery remain separate from native cast. No SAM silhouette is used as a cel.\n\nLinear vector interpolation is a baseline, not an approved performance. Recognition, final mask fit, material contacts and normal-speed playback require separate evidence. Still-image approval cannot make a training pair eligible. No training ran.\n')
    print(json.dumps(dict(subject=subject, frames=count, keys=len(key_frames), native_topology=topology, trace=trace, movies=validation), allow_nan=False))
    return shot


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', metavar='SUBJECT')
    parser.add_argument('--refresh-page', action='store_true', help='Refresh review note/summary/revision from config without rerendering media')
    parser.add_argument('--subject')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path, help='Optional scratch output for technical checks; config inputs stay relative to config')
    args = parser.parse_args()
    if args.snapshot:
        snapshot(args.snapshot)
    elif args.refresh_page:
        assert args.config, '--config is required'
        refresh_page(args.config, args.output)
    else:
        assert args.subject and args.config and args.source, '--subject, --config and --source are required'
        build(args.subject, args.config, args.source, args.output)
