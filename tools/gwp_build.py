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
        cands.append((cost, r['key_id'], st))
    cands.sort(key=lambda c: c[0]); _, kid, st = cands[skip]
    P = np.concatenate(st); mn, mx = P.min(0), P.max(0)
    out = [((s - mn) / (mx - mn) * [x1 - x0, y1 - y0] + [x0, y0]).round(1).tolist() for s in st]
    return kid, out


def build(cat):
    src = ROOT / 'shots' / f'{cat}-sam'; out = ROOT / 'shots' / f'{cat}-gwp'; out.mkdir(exist_ok=True)
    if (out / 'frames').exists(): shutil.rmtree(out / 'frames')
    shutil.copytree(src / 'frames', out / 'frames')
    for fn in ('clip.json', 'masks.json', 'silhouettes.png'):
        if (src / fn).exists(): shutil.copy(src / fn, out / fn)
    poses = sorted(src.glob('pose_agent_v*.json'), key=lambda p: int(re.findall(r'v(\d+)', p.name)[0]))[-1]
    for p in src.glob('pose_*.json'): shutil.copy(p, out / p.name)
    if (src / 'rig_params.json').exists(): shutil.copy(src / 'rig_params.json', out / 'rig_params.json')
    frames, keys = inbetween(out, ROOT / 'rigs' / f'{cat}.py', poses)
    clip = json.load(open(out / 'clip.json')); n, W, H = clip['n'], clip['W'], clip['H']
    sc = json.load(open(ROOT / 'rigs' / f'{cat}_scene.json')); spec = json.load(open(ROOT / 'rigs' / f'{cat}_spec.json'))
    cx = sc['camera']['x'] if isinstance(sc['camera']['x'], list) else [0] * n
    cy = sc['camera']['y'] if isinstance(sc['camera'].get('y'), list) else [0] * n
    cam = [[round(float(cx[f]), 1), round(float(cy[f]), 1)] for f in range(n)]
    objs = []
    for o in sc['objects']:
        if 'qd' in o:
            kid, st = qd_fit(o['qd'], o['box'], o.get('strokes'), o.get('skip', 0), o.get('aspect'))
            objs.append({'id': o['id'], 'plane': o['plane'], 'z': next(p['z'] for p in sc['planes'] if p['id'] == o['plane']), 'class': o['qd'],
                         'source': f'quickdraw:{kid}', 'strokes': st})
        else:
            objs.append({'id': o['id'], 'plane': o['plane'], 'z': next(p['z'] for p in sc['planes'] if p['id'] == o['plane']), 'class': o.get('class', 'line'),
                         'source': 'drawn by agent: ' + o['why'], 'strokes': o['strokes']})
    M = json.load(open(out / 'masks.json'))
    notes = sc.get('notes', {})
    S = {'title': f"{cat.capitalize()}, the Giraffe Walks Past way", 'category': cat, 'fps': clip['fps'], 'W': W, 'H': H, 'z_ref': sc['z_ref'],
         'source': {'film': clip.get('source_title', 'Moving Image Archive'), 'url': json.load(open(ROOT / f'batches/2026-10-20-selected-drawings/subjects/{cat}/source.json'))['source']['shot_page_url']},
         'planes': sc['planes'], 'camera': cam, 'objects': objs,
         'cast': {'id': cat, 'plane': 'char', 'frames': frames, 'keys': keys, 'source': f"quickdraw:{spec['doodle_key_id']} as a rig ({len(spec['parts'])} parts, root {spec['root'][0]} to {spec['root'][1]}); {len(keys)} keys placed by eye over SAM silhouettes ({poses.name})"},
         'xsheet': [{'f': f, 'drawing': (f'K{keys.index(f) + 1:02d}' if f in keys else f'I{f:02d}'), 'kind': 'K' if f in keys else 'I', 'cam': cam[f], 'note': notes.get(str(f), '')} for f in range(n)],
         'footage': [f'frames/f{f:03d}.jpg' for f in range(n)], 'masks': [M[str(f)] for f in range(n)],
         'camera_source': sc['camera'].get('source', '')}
    json.dump(S, open(out / 'shot.json', 'w'), separators=(',', ':'))
    print(cat, n, 'frames', len(keys), 'keys', len(objs), 'objects')
    return S


if __name__ == '__main__':
    for c in sys.argv[1:]: build(c)
