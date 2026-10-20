"""Assemble a shot made the Giraffe Walks Past way: shots/<cat>-gwp/.

Inputs (all hand-made per subject except the SAM run):
  shots/<cat>-sam/        frames, SAM masks, clip.json (from the SAM run)
  rigs/<cat>.py, rigs/<cat>_spec.json   the rig: the chosen doodle itself, bent at joints
  shots/<cat>-sam/pose_agent_v*.json    keys placed by eye over the silhouettes (latest version used)
  rigs/<cat>_scene.json   planes, camera and scenery: each object either a real Quick, Draw! doodle of a
                          named category fitted into a box placed by eye (picked by shape: aspect ratio and
                          stroke count closest to the target), or strokes drawn by the agent, with a reason
usage: python3 tools/gwp_build.py <cat>
"""
import json, shutil, sys, glob, re
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'rigs')); sys.path.insert(0, str(ROOT / 'tools'))
from inbetween import run as inbetween


def qd_fit(cat, box, want_strokes=None, skip=0, aspect=None):
    rows = [json.loads(l) for l in open(ROOT / f'data/quickdraw/{cat}.part').read().splitlines()[:-1]]
    x0, y0, x1, y1 = box; ta = aspect or (x1 - x0) / max(y1 - y0, 1)
    cands = []
    for r in rows[:3000]:
        if not r['recognized']: continue
        st = [np.array(list(zip(*s)), float) for s in r['drawing']]
        P = np.concatenate(st); w, h = np.ptp(P[:, 0]), np.ptp(P[:, 1])
        if w < 10 or h < 10: continue
        cost = abs(np.log((w / h) / ta)) + (0.08 * abs(len(st) - want_strokes) if want_strokes else 0)
        # a stray long line makes the bounding box much bigger than the drawing: prefer compact drawings
        core = np.ptp(np.percentile(P, [10, 90], axis=0), axis=0) / np.maximum([w, h], 1)
        cost += 1.5 * max(0.0, 0.55 - float(core.min()))
        cands.append((cost, r['key_id'], st))
    cands.sort(key=lambda c: c[0]); _, kid, st = cands[skip]
    P = np.concatenate(st); mn, mx = P.min(0), P.max(0)
    out = [((s - mn) / (mx - mn) * [x1 - x0, y1 - y0] + [x0, y0]).round(1).tolist() for s in st]
    return kid, out


def source_record(cat):
    p = ROOT / f'batches/2026-10-20-selected-drawings/subjects/{cat}/source.json'
    if not p.exists(): p = ROOT / 'shots' / cat / 'source.json'
    j = json.load(open(p)); return j.get('source', j)


def build(cat):
    src = ROOT / 'shots' / f'{cat}-sam'; out = ROOT / 'shots' / f'{cat}-gwp'; out.mkdir(exist_ok=True)
    if (out / 'frames').exists(): shutil.rmtree(out / 'frames')
    shutil.copytree(src / 'frames', out / 'frames')
    for fn in ('clip.json', 'masks.json', 'silhouettes.png'):
        if (src / fn).exists(): shutil.copy(src / fn, out / fn)
    pv = sorted(src.glob('pose_agent_v*.json'), key=lambda p: int(re.findall(r'v(\d+)', p.name)[0]))
    poses = pv[-1] if pv else Path('none')
    for p in src.glob('pose_*.json'): shutil.copy(p, out / p.name)
    if (src / 'rig_params.json').exists(): shutil.copy(src / 'rig_params.json', out / 'rig_params.json')
    rn = cat.replace('-', '_'); spec0 = json.load(open(ROOT / 'rigs' / f'{rn}_spec.json'))
    if 'field' in spec0:
        from field import frames as field_frames
        c0 = json.load(open(out / 'clip.json')); frames = field_frames(out, spec0, c0['n'], c0['W'], c0['H']); keys = c0['keys']
    else:
        frames, keys = inbetween(out, ROOT / 'rigs' / f'{rn}.py', poses)
    clip = json.load(open(out / 'clip.json')); n, W, H = clip['n'], clip['W'], clip['H']
    sc = json.load(open(ROOT / 'rigs' / f'{rn}_scene.json')); spec = json.load(open(ROOT / 'rigs' / f'{rn}_spec.json'))
    # plane depths from Depth Anything (shots/<cat>-sam/depth.json, relative inverse depth, 1 = near): a plane
    # with z_from_depth takes z = z_char x subject depth / band depth, so far scenery slides slower by measurement
    if (src / 'depth.json').exists():
        dj = json.load(open(src / 'depth.json')); med = lambda k: float(np.median([x[k] for x in dj if x.get(k)]))
        zc = next(p['z'] for p in sc['planes'] if p['id'] == 'char'); subj = med('subject')
        for p in sc['planes']:
            if p.get('z_from_depth'):
                p['z'] = round(float(np.clip(zc * subj / max(med(p['z_from_depth']), 1e-3), 1.1, 12)), 2)
                p['label'] += f" (depth {med(p['z_from_depth']):.2f} vs subject {subj:.2f})"
    cx = sc['camera']['x'] if isinstance(sc['camera']['x'], list) else [0] * n
    cy = sc['camera']['y'] if isinstance(sc['camera'].get('y'), list) else [0] * n
    cam = [[round(float(cx[f]), 1), round(float(cy[f]), 1)] for f in range(n)]
    objs = []
    for o in sc['objects']:
        if o.get('copy_of_design'):   # the chosen doodle itself, small, as extras (a flock, a herd)
            P = np.concatenate([np.array(q, float) for q in spec['strokes']]); mn, mx = P.min(0), P.max(0); x0, y0, x1, y1 = o['box']
            sc_ = min((x1 - x0) / (mx - mn)[0], (y1 - y0) / (mx - mn)[1])
            st = [(((np.array(q, float) - mn) * [(-1 if o.get('mirror') else 1), 1] + ([mx[0] - mn[0], 0] if o.get('mirror') else [0, 0])) * sc_ + [x0, y0]).round(1).tolist() for q in spec['strokes']]
            objs.append({'id': o['id'], 'plane': o['plane'], 'z': next(p['z'] for p in sc['planes'] if p['id'] == o['plane']), 'class': spec['category'],
                         'source': f"quickdraw:{spec['doodle_key_id']} (the character's own doodle, repeated small)", 'strokes': st})
        elif 'qd' in o:
            kid, st = qd_fit(o['qd'], o['box'], o.get('strokes'), o.get('skip', 0), o.get('aspect'))
            objs.append({'id': o['id'], 'plane': o['plane'], 'z': next(p['z'] for p in sc['planes'] if p['id'] == o['plane']), 'class': o['qd'],
                         'source': f'quickdraw:{kid}', 'strokes': st})
        else:
            objs.append({'id': o['id'], 'plane': o['plane'], 'z': next(p['z'] for p in sc['planes'] if p['id'] == o['plane']), 'class': o.get('class', 'line'),
                         'source': 'drawn by agent: ' + o['why'], 'strokes': o['strokes']})
    M = json.load(open(out / 'masks.json'))
    notes = sc.get('notes', {})
    S = {'title': f"{cat.capitalize()}, the Giraffe Walks Past way", 'category': cat, 'fps': clip['fps'], 'W': W, 'H': H, 'z_ref': sc['z_ref'],
         'source': {'film': clip.get('source_title', 'Moving Image Archive'), 'url': source_record(cat).get('shot_page_url', '')},
         'planes': sc['planes'], 'camera': cam, 'objects': objs,
         'cast': {'id': cat, 'plane': 'char', 'frames': frames, 'keys': keys, 'source': (f"quickdraw:{spec['doodle_key_id']} as a rig ({len(spec['parts'])} parts, root {spec['root'][0]} to {spec['root'][1]}); {len(keys)} keys placed by eye over SAM silhouettes ({poses.name})" if 'field' not in spec else f"quickdraw:{spec['doodle_key_id']} as a field of marks ({len(spec['field']['layers'])} layers); " + spec['field']['motion'])},
         'xsheet': [{'f': f, 'drawing': (f'K{keys.index(f) + 1:02d}' if f in keys else f'I{f:02d}'), 'kind': 'K' if f in keys else 'I', 'cam': cam[f], 'note': notes.get(str(f), '')} for f in range(n)],
         'footage': [f'frames/f{f:03d}.jpg' for f in range(n)], 'masks': [M[str(f)] if ('field' not in spec and not sc.get('no_cel')) else [] for f in range(n)],
         'camera_source': sc['camera'].get('source', '')}
    json.dump(S, open(out / 'shot.json', 'w'), separators=(',', ':'))
    print(cat, n, 'frames', len(keys), 'keys', len(objs), 'objects')
    return S


if __name__ == '__main__':
    for c in sys.argv[1:]: build(c)
