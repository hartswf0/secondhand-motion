"""Drawn keys for the dragon (shots/dragon/drawn/k###.json), made from the rig drawing at each rig key.
Changes: the chest/jaw line (stroke 1) is redrawn as one line from the chin to its still foot with the doodle's
own slight bend; an extra nose-horn stroke (the film's horn, which the doodle has no stroke for) sits on the
front of the snout and turns with the head, so the head's tilt reads."""
import json, sys, math
from pathlib import Path
import numpy as np
D = Path(__file__).resolve().parent.parent / 'drawn'
WHY = {
 0: 'pull-back starts: the dragon fills the frame, nose down; drawn so the chest line runs straight from chin to foot',
 1: 'pull-back, second of three steps: the same pose smaller',
 2: 'pull-back, third step: the same pose smaller again',
 3: 'pull-back lands; nose down at its lowest of the opening, the start of the head lift',
 4: 'the painting holds; the head starts to rise about the back of the skull',
 6: 'breakdown of the lift: nose and horn halfway up, chest line follows the chin',
 10: 'nearly up: the head slows into the top of the lift',
 13: 'THE LINE: head tipped back, nose and horn at their highest; the clearest drawing of the shot',
 16: 'the head starts down again after the short hold',
 19: 'breakdown of the drop: halfway down',
 23: 'extreme: head tipped forward and down, horn lowered toward the claws',
 27: 'the head starts to lift again',
 31: 'last frame: head on its way up, as the film leaves it',
}
def bend(a, b):  # the doodle's own stroke 1: (29,119)->(33,150)->(38,162); mid at 72% with a small sideways bow
    a, b = np.array(a), np.array(b); v = b - a; n = np.array([-v[1], v[0]]) / max(np.hypot(*v), 1e-6)
    m = a + 0.72 * v + n * 0.04 * np.hypot(*v)
    return [a.tolist(), m.round(1).tolist(), b.tolist()]
def horn(h, s):
    h = np.array(h); piv = h[0]; snout = (h[3] + h[4]) / 2; d = snout - piv; L = np.hypot(*d); u = d / L
    up = np.array([u[1], -u[0]]); up = up if up[1] < 0 else -up   # perpendicular toward the top of the head
    base = h[3] + 0.3 * (h[2] - h[3])
    tip = base + u * 0.42 * L + up * 0.95 * L
    mid = base + u * 0.36 * L + up * 0.42 * L
    return [base.round(1).tolist(), mid.round(1).tolist(), tip.round(1).tolist()]
for f, why in WHY.items():
    p = D / f'k{f:03d}.json'; K = json.load(open(p))
    st = K['strokes']; st[1] = bend(st[1][0], st[1][-1])
    K['why'] = why; K['extra'] = {'horn': horn(st[0], st)}
    json.dump(K, open(p, 'w'))
json.dump({'line': 13, 'line_why': 'the dragon lifts its head: nose and horn at their highest at frame 13, after a slow rise from frame 3, held one frame before it sinks', 'holds': [[13, 14]]}, open(D / 'xsheet.json', 'w'), indent=1)
