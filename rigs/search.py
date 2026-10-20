"""Rig parameter search, as Giraffe Walks Past step 6: score = likeness to the chosen doodle's stroke statistics x fit to the SAM silhouette x
(0.5 + typicality/200), means over keys. Typicality is among real Quick, Draw! drawings of the category
(tools/style_score.py); likeness is to the one doodle the character must stay. The classifier term runs separately in the browser (it is not available in this container).
usage: python3 rigs/search.py <shot_dir> <rig.py> <poses.json> <category> '<json grid>'"""
import json, sys, itertools, importlib.util
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from style_score import style
from sam_keys import raster, fit_score
sys.path.insert(0, str(ROOT / 'shots' / 'giraffe-walks-past'))
from reward import feats
from style_score import ref as style_ref

d, rigp, posep, cat, grid = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], json.loads(sys.argv[5])
spec = importlib.util.spec_from_file_location('rig', rigp); rig = importlib.util.module_from_spec(spec); spec.loader.exec_module(rig)
P = json.load(open(posep)); M = json.load(open(d / 'masks.json')); W, H = 384, 288
keys = sorted(int(k) for k in P)
# likeness to the chosen doodle: distance between stroke statistics, in units of the category's spread
dj = json.load(open(ROOT / f'batches/2026-10-20-selected-drawings/subjects/{cat}/design.json'))
dd = json.loads(dj['drawing']) if isinstance(dj['drawing'], str) else dj['drawing']
fd = feats([list(zip(*q)) for q in dd])
R = style_ref(cat); sd = R[2] if isinstance(R, tuple) and len(R) > 2 else None
def like(strokes):
    z = (feats(strokes) - fd) / (sd if sd is not None else 1)
    return float(np.exp(-np.sqrt((z ** 2).mean())))
masks = {k: raster(M[str(k)], W, H) for k in keys}
rows = []
names = list(grid)
for combo in itertools.product(*[grid[n] for n in names]):
    prm = dict(zip(names, combo))
    st = [style(rig.draw(P[str(k)], prm), cat) for k in keys]
    ft = [fit_score(rig.draw(P[str(k)], prm), masks[k]) for k in keys if masks[k].any()]
    lk = [like(rig.draw(P[str(k)], prm)) for k in keys]
    rows.append({'params': prm, 'style': round(float(np.mean(st)), 1), 'like_doodle': round(float(np.mean(lk)), 3), 'fit': round(float(np.mean(ft)), 3),
                 'score': round(float(np.mean(lk)) * float(np.mean(ft)) * (0.5 + float(np.mean(st)) / 200), 4)})
rows.sort(key=lambda r: -r['score'])
json.dump(rows, open(d / 'rig_search.json', 'w'), indent=0)
json.dump(rows[0]['params'], open(d / 'rig_params.json', 'w'))
for r in rows[:6]: print(r)
print(len(rows), 'combinations')
