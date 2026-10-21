"""Rain: the downpour that builds over the shot, drawn with the doodle's own nine dashes.

The cast is the field rig (rigs/field.py, spec['field']): a light, steady rain over the whole frame. This file
draws the second copy of that rain, used by the scene object "downpour" (rigs/rain_scene.json, rig_poses):
the curtain that thickens over the footbridge and the splashes on its deck. A pose is

  {"t": frame, "heavy": 0..1, "splash": 0..1, "spread": 0..1}

  t       time in frames; drops fall at a fixed speed in t, splashes are re-placed every 3 frames
  heavy   share of the curtain's drops that are drawn (centre of the bridge first), and how much longer they are
  splash  share of the splash marks that are drawn
  spread  how far from the bottom centre of the deck the splashes may land (1 = the whole deck and the water
          to the left of the left rail, where the film's splashes reach at the peak)

Every mark is one of the doodle's strokes (quickdraw rain 5897326906310656): a curtain drop is one dash, scaled;
a splash is two of its dashes splayed into a V, small, the size falling off with distance up the bridge.
"""
import json
from pathlib import Path
import numpy as np

_S = json.load(open(Path(__file__).with_name('rain_spec.json')))
DASH = [np.array(s, float) for s in _S['strokes']]
DASH = [s - [s[:, 0].mean(), s[:, 1].min()] for s in DASH]       # each dash: top at y 0, centred in x

W, H = 384, 288
_r = np.random.default_rng(23)
NC = 240
CX = np.clip(200 + _r.normal(0, 78, NC), 70, 340)               # curtain drops crowd the middle of the bridge
CY = _r.uniform(0, 250, NC)
CT = 0.8 * _r.uniform(0, 1, NC) + 0.2 * np.abs(CX - 200) / 140   # order of appearance: centre first
CK = np.arange(NC) % len(DASH)
NS = 110
ST = _r.uniform(0, 1, NS)
DECK = np.array([[168, 162], [216, 162], [384, 258], [384, 288], [0, 288], [0, 252]], float)
LEFT_WATER = np.array([[10, 176], [128, 172], [20, 214]], float)


def _inside(p, poly):
    x, y = p; c = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c


def _splash_at(slot, cyc, spread):
    g = np.random.default_rng(slot * 7919 + cyc * 104729)
    for _ in range(14):
        if spread > 0.75 and g.uniform() < 0.35 * (spread - 0.75) / 0.25:
            p = np.array([g.uniform(10, 128), g.uniform(172, 214)])
            if _inside(p, LEFT_WATER): return p
            continue
        p = np.array([g.uniform(0, W), g.uniform(162, 286)])
        if not _inside(p, DECK): continue
        d = np.hypot((p[0] - 192) / 200, (p[1] - 286) / 124)          # 0 at the bottom centre, about 1 at the far end
        if d <= 0.28 + 0.8 * spread: return p
    return None


def draw(pose):
    t = pose['t']; heavy = pose['heavy']; spl = pose['splash']; spread = pose['spread']
    out = []
    stretch = 1 + 0.45 * heavy
    for i in range(NC):
        if CT[i] >= heavy: continue
        y = (CY[i] + 9.5 * t) % 260 - 40
        s = DASH[CK[i]] * [0.5, 0.5 * stretch] + [CX[i] - 0.06 * y, y]
        if s[:, 1].min() > (204 if i % 4 == 0 else 168): continue      # the curtain ends at the water line; a few drops reach the deck
        out.append(np.round(s, 1).tolist())
    for j in range(NS):
        if ST[j] >= spl: continue
        cyc = int((t + j % 3) // 3)
        p = _splash_at(j, cyc, spread)
        if p is None: continue
        k = 0.07 + 0.15 * (p[1] - 160) / 128
        for side, kk in ((-1, (j + cyc) % 5), (1, (j + cyc + 2) % 5)):  # two of the dashes, splayed wide
            d = DASH[kk] * k; d = d - [0, d[:, 1].max()]                  # bottom of the dash at the splash point
            a = np.radians(42 * side); R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
            out.append(np.round(d @ R.T + p + [side * 2.0, 0], 1).tolist())
    return out
