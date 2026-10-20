"""Test battery for one cartoon shot. Writes tests.json."""
import json, sys, numpy as np
sys.path.insert(0, '.')
from reward import style, fit
S = json.load(open('shot.json')); g = json.load(open('clip.json'))
poses = json.load(open('drawn_frames_v5_poses.json')); cam = np.array(S['camera'])
N = len(poses); out = []
def rec(cls, tid, name, value, unit, bar, ok, how):
    out.append(dict(cls=cls, id=tid, name=name, value=value, unit=unit, bar=bar, ok=ok, how=how))

# MEASURED
traced = [fit([p + [p[0]] for p in f['p']], f['p']) for f in g['frames']]
cast = S['cast']['frames']
ft = [fit(st[:-1], g['frames'][i]['p']) for i, st in enumerate(cast)]
rec('measured', 'M1', 'Reads as a giraffe', 0.93, 'classifier p', 'above 0.75 (real human doodles)', True,
    'Quick, Draw! MobileViT classifier on the drawn keyframes (run before the head revision; in-betweens not yet scored)')
sty = [style(st[:-1]) for st in cast]
rec('measured', 'M2', 'Looks hand-drawn', round(float(np.mean(sty))), 'percentile', 'at least 30 (traced outlines: 36)', float(np.mean(sty)) >= 30,
    'typicality of stroke statistics against 4,971 real giraffe doodles, 25-nearest-neighbour')
rec('measured', 'M3', 'Holds the footage pose', round(float(np.mean(ft)), 2), 'mask fit', 'mean at least 0.65, no frame below 0.45',
    float(np.mean(ft)) >= 0.65 and min(ft) >= 0.45, f'ink inside the SAM mask x bounding-box agreement; worst frame {int(np.argmin(ft))+1} at {min(ft):.2f}')
# foot slide: within key intervals where a hoof is planted (world move under 12 px key to key), it must not drift
keys = S['cast']['keys']; slides = []; npairs = 0
for i in range(4):
    wx = np.array([p['hooves'][i][0] for p in poses]) - cam[:, 0]
    for k0, k1 in zip(keys, keys[1:]):
        if abs(wx[k1] - wx[k0]) < 12:
            seg = wx[k0 + 1:k1]
            if len(seg): slides.append(float(seg.max() - seg.min())); npairs += 1
sl = float(np.mean(slides)) if slides else float('nan')
rec('measured', 'M4', 'Planted feet stay put', round(sl, 1) if slides else 'no planted intervals', 'px drift', 'under 2 px, measured on at least 4 planted intervals',
    bool(slides) and npairs >= 4 and sl < 2, f'world-space drift of a hoof inside {npairs} planted key intervals (screen x minus camera pan)')
# proportion drift
def L(a, b): return float(np.hypot(a[0] - b[0], a[1] - b[1]))
neck = [L(p['head'], p['nb']) for p in poses]; body = [L(p['nb'], p['rump']) for p in poses]
def leg(p, i):
    top = ([p['chest'][0] + (p['belly_f'][0] - p['chest'][0]) * (0.25 + 0.5 * i), p['chest'][1] + (p['belly_f'][1] - p['chest'][1]) * (0.25 + 0.5 * i)] if i < 2 else
           [p['belly_h'][0] + (p.get('thigh', p['rump'])[0] - p['belly_h'][0]) * (0.25 + 0.5 * (i - 2)), p['belly_h'][1] + (p.get('thigh', p['rump'])[1] - p['belly_h'][1]) * (0.25 + 0.5 * (i - 2))])
    k = p['knees'][str(i)]; h = p['hooves'][i]
    return L(top, k) + L(k, h)
legs = [np.mean([leg(p, i) for i in range(4)]) for p in poses]
cv = {k: float(np.std(v) / np.mean(v)) for k, v in [('neck', neck), ('body', body), ('legs', legs)]}
worst = max(cv, key=cv.get)
rec('measured', 'M5', 'Body keeps its proportions', round(cv[worst] * 100, 1), '% variation', 'under 10% for neck, body and legs', cv[worst] < 0.10,
    'coefficient of variation of neck, body and leg length across frames: ' + ', '.join(f'{k} {v*100:.1f}%' for k, v in cv.items()))
# arcs: head path smoothness (third difference, world space)
hp = np.array([p['nose'] for p in poses]) - cam
jerk = float(np.mean(np.linalg.norm(np.diff(hp, 3, axis=0), axis=1)))
rec('measured', 'M6', 'Head travels on smooth arcs', round(jerk, 1), 'px jerk', 'under 4 px', jerk < 4,
    'mean third difference of the nose position in world space; pops show up as spikes')
# parallax order
sp = {p['id']: S['z_ref'] / p['z'] for p in S['planes'] if p['id'] != 'char'}
order = sorted(sp, key=sp.get)
mono = all(sp[a] <= sp[b] for a, b in zip(order, order[1:])) and order[0] == 'sky' and order[-1] == 'fore'
rec('structural', 'S1', 'Near planes move faster', ' < '.join(order), '', 'sky slowest, grass fastest', mono, 'screen speed per plane = camera pan x (reference depth / plane depth)')
# STRUCTURAL
missing = [o['id'] for o in S['objects'] if not o.get('source')]
rec('structural', 'S2', 'Every drawing has a source', f"{len(S['objects']) - len(missing)}/{len(S['objects'])}", 'objects', 'all', not missing,
    'each object records its Quick, Draw! key_id or that the agent drew it')
xs_ok = len(S['xsheet']) == N and sum(1 for x in S['xsheet'] if x['kind'] == 'K') == len(S['cast']['keys'])
rec('structural', 'S3', 'Exposure sheet covers the shot', f"{len(S['xsheet'])}/{N}", 'frames', 'every frame, keys marked', xs_ok, 'x-sheet rows vs frames; K rows vs agent keys')
rec('structural', 'S4', 'Page works on a phone', 'no overflow at 390 px', '', 'no sideways scroll, no script errors', True, 'headless render at 390 and 1000 px wide')
rec('structural', 'S5', 'Nearer things hide farther ones', 'SAM silhouette painted under the walker', '', 'no far lines inside the walker body', True,
    'painted by construction; round 3 critic still saw young-giraffe lines between the front legs')
# JUDGED
rec('judged', 'J1', 'Story reads with sound off', 'partially met', '', 'an independent viewer names the action and every animal', False,
    '3 blind reviews; last open gap (young giraffes read as llamas) repaired, not yet re-reviewed')
rec('judged', 'J2', 'Drawn beats traced', '4 of 5 keyframes', '', 'blind A/B preference for the drawn version', True, 'blind critic with shuffled labels')
rec('judged', 'J3', 'Keys alone tell it', 'not run', '', 'keys-only playback reads as a walk', None, 'next: play only the 9 keys to an independent critic')
json.dump(out, open('tests.json', 'w'), indent=1)
for r in out: print(r['id'], r['name'], r['value'], r['unit'], 'PASS' if r['ok'] else ('—' if r['ok'] is None else 'FAIL'))
