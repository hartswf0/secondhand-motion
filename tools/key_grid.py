"""Key frames enlarged with a numbered grid and the SAM outline, for placing rig points by eye.
usage: python3 tools/key_grid.py <shot_dir> <out.png> f1 f2 ... [--pose poses.json --rig rigs/x.py]"""
import json, sys, importlib.util
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent)); from sam_keys import raster
a = [x for x in sys.argv[1:] if not x.startswith('--')]
d = Path(a[0]); out = a[1]
pose = rig = None
if '--pose' in sys.argv:
    pose = json.load(open(sys.argv[sys.argv.index('--pose') + 1])); a = [x for x in a if x != sys.argv[sys.argv.index('--pose') + 1]]
if '--rig' in sys.argv:
    rp = sys.argv[sys.argv.index('--rig') + 1]; a = [x for x in a if x != rp]
    spec = importlib.util.spec_from_file_location('rig', rp); rig = importlib.util.module_from_spec(spec); spec.loader.exec_module(rig)
fr = [int(x) for x in a[2:]]
M = json.load(open(d / 'masks.json')); clip = json.load(open(d / 'clip.json')); W, H = clip['W'], clip['H']; S = 2
prm = json.load(open(d / 'rig_params.json')) if (d / 'rig_params.json').exists() else {}
tiles = []
for f in fr:
    im = Image.open(d / 'frames' / f'f{f:03d}.jpg').convert('RGB'); im = Image.blend(im, Image.new('RGB', im.size, 'white'), .3).resize((W * S, H * S))
    dr = ImageDraw.Draw(im)
    for x in range(0, W, 10): dr.line([(x * S, 0), (x * S, H * S)], fill=(0, 60, 255) if x % 50 == 0 else (160, 190, 255), width=1)
    for y in range(0, H, 10): dr.line([(0, y * S), (W * S, y * S)], fill=(0, 60, 255) if y % 50 == 0 else (160, 190, 255), width=1)
    for x in range(0, W, 50): dr.text((x * S + 2, 2), str(x), fill=(0, 0, 160))
    for y in range(50, H, 50): dr.text((2, y * S + 2), str(y), fill=(0, 0, 160))
    m = raster(M[str(f)], W, H).astype(np.uint8); cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for c in cs: dr.line([(p[0][0] * S, p[0][1] * S) for p in c] + [(c[0][0][0] * S, c[0][0][1] * S)], fill=(230, 0, 0), width=2)
    if pose and str(f) in pose:
        P = pose[str(f)]
        if rig:
            for s in rig.draw(P, prm): dr.line([(x * S, y * S) for x, y in s], fill=(0, 0, 0), width=3)
        for k, v in P.items():
            if isinstance(v, list) and len(v) == 2 and not isinstance(v[0], list):
                dr.ellipse([v[0] * S - 4, v[1] * S - 4, v[0] * S + 4, v[1] * S + 4], fill=(255, 140, 0)); dr.text((v[0] * S + 5, v[1] * S - 5), k, fill=(120, 40, 0))
    dr.text((W * S - 40, 4), f'f{f}', fill='black'); tiles.append(im)
cols = 2; G = Image.new('RGB', (W * S * cols, H * S * ((len(tiles) + cols - 1) // cols)), 'white')
for i, t in enumerate(tiles): G.paste(t, ((i % cols) * W * S, (i // cols) * H * S))
G.save(out)
