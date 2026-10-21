"""Generate the duck's drawn keys (k###.json) from three head drawings of the doodle:
profile (the doodle's own head, moved onto the film duck's head), front (the same outline points
redrawn as a round head seen from the front, the bill hanging down the middle, the two eye dots one
either side) and blends between them for the turn. Tears are extra strokes (the doodle has none).
Run: python3 shots/duck/drawn/gen_keys.py
"""
import json
from pathlib import Path
import numpy as np

D = Path(__file__).resolve().parent
ROOT = D.parent.parent.parent
R = json.load(open(ROOT / 'shots/duck-gwp/rig_frames.json'))
BASE = [np.array(s, float) for s in R[0]]
HEAD0 = list(range(0, 12)) + [24, 25, 26]      # stroke-0 points that belong to head and neck

# ---- profile: the rig head moved onto the film duck's head (head +36, -18), neck blended into the body
def profile():
    S = [s.copy() for s in BASE]
    d = np.array([36.0, -18.0])
    for i, p in enumerate(S[0]):
        w = float(np.clip((150 - p[1]) / 45, 0, 1)) if i not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 25, 26) else 1.0
        S[0][i] = p + d * w
    for k in (1, 2, 3): S[k] = S[k] + d
    return S

# ---- front: head centre about (218, 72); round head, bill down the middle, eyes either side
def front():
    S = [s.copy() for s in BASE]
    pts = {0: (229, 93), 1: (229, 114), 2: (220, 124), 3: (210, 114), 4: (209, 93),   # bill: base right, down, tip, up, base left
           5: (197, 90), 6: (190, 72), 7: (197, 54), 8: (216, 47), 9: (235, 53),       # left cheek, up over the top
           10: (244, 71), 11: (240, 92),                                                 # right cheek, right jaw
           24: (194, 128), 25: (200, 95), 26: (236, 94)}                                 # neck left, chin line across
    for i, xy in pts.items(): S[0][i] = np.array(xy, float)
    S[0][12] = np.array([236.0, 128.0])     # back of the neck comes down from the right jaw
    S[1] = np.array([[205.0, 70.0], [205.0, 70.0]])     # the doodle's two eye dots: one each side
    S[2] = np.array([[230.0, 70.0], [230.0, 70.0]])
    S[3] = np.array([[219.0, 97.0], [219.0, 113.0]])    # the bill line, now down the bill's middle
    return S

# ---- three-quarter: the head round like the front view, the bill short and pointing down to our left
def three_q():
    S = [s.copy() for s in BASE]
    pts = {0: (210, 100), 1: (192, 115), 2: (185, 115), 3: (183, 108), 4: (199, 90),
           5: (196, 72), 6: (201, 54), 7: (218, 47), 8: (235, 53), 9: (243, 69),
           10: (242, 87), 11: (237, 98), 24: (192, 128), 25: (200, 112), 26: (207, 103)}
    for i, xy in pts.items(): S[0][i] = np.array(xy, float)
    S[0][12] = np.array([233.0, 130.0])
    S[1] = np.array([[203.0, 66.0], [203.0, 66.0]])
    S[2] = np.array([[226.0, 64.0], [226.0, 64.0]])
    S[3] = np.array([[187.0, 110.0], [203.0, 97.0]])
    return S

P, F, Q = profile(), front(), three_q()

def blend(t, dx=0.0, dy=0.0, bill=0.0, tilt=0.0):
    """t 0 profile .. 1 front; dx, dy move the head; bill swings the bill tip sideways (px, + to our left);
    tilt rotates the head about the neck (degrees)."""
    if t <= 0.5: u = t / 0.5; S = [P[k] * (1 - u) + Q[k] * u for k in range(len(P))]
    else: u = (t - 0.5) / 0.5; S = [Q[k] * (1 - u) + F[k] * u for k in range(len(P))]
    head_idx = {0: HEAD0}
    piv = np.array([215.0, 100.0])
    a = np.radians(tilt); M = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    def mv(p, w=1.0):
        q = piv + (p - piv) @ M.T + np.array([dx, dy])
        return p + (q - p) * w
    for i in HEAD0:
        w = 1.0 if i not in (24,) else 0.5
        S[0][i] = mv(S[0][i], w)
    S[0][12] = mv(S[0][12], 0.4)
    for k in (1, 2, 3): S[k] = np.array([mv(p) for p in S[k]])
    if bill:   # tip of the bill (points 1-3 and the end of stroke 3) swings sideways
        for i, w in ((1, .8), (2, 1), (3, .8)): S[0][i] = S[0][i] + np.array([-bill * w, -abs(bill) * .25 * w])
        S[3][1] = S[3][1] + np.array([-bill * .8, -abs(bill) * .2])
    for k in (1, 2):   # the eye dots: a tap of the pen, drawn as a 2 px dash so they show
        S[k] = np.array([S[k][0], S[k][0] + [1.5, 1.0]])
    return S

def drop(x, y, s=1.0):
    """a tear in the doodle's hand: a pointed top and a round-ish bottom, five straight segments"""
    sh = np.array([[0, -7], [3.5, 0], [2.5, 3.5], [-2.5, 3.5], [-3.5, 0], [0, -7]], float) * s
    return (sh + [x, y]).round(1).tolist()

# ---- head keys: frame -> (t, dx, dy, bill, tilt, why)
HEAD = {
    0: (0.0, 0, 0, 0, 0, "Profile, looking left with the bill out flat: the doodle's own head on the film duck's head."),
    4: (0.0, 0, 1, 0, 2, "Still profile, the bill just starting to drop: the hold before the turn."),
    5: (0.15, -2, 3, 0, 5, "Anticipation: the head dips and the bill shortens as it starts to swing toward us (film frame 5)."),
    6: (0.85, 0, 2, 0, 0, "The line: the head has turned to face us, bill pointing down, both eyes showing (film frame 6)."),
    7: (1.0, 0, 3, 0, 0, "The bill settles straight down the middle of the face."),
    8: (1.0, 0, 4, 0, -2, "Settle: the head sinks a little and tips, the sad look the crying starts from."),
    12: (1.0, 0, 3, 0, 0, "Facing us, still; the bill a little lower, the moment before the tears."),
    16: (1.0, 0, 4, 1, -2, "First tears leave both eyes; the head bows slightly."),
    20: (1.0, 0, 3, -1, 1, "Crying: tears on the chest, one landing between the feet."),
    24: (1.0, 0, 4, 1, -1, "Crying: the bill drifts a little left with the sobs."),
    28: (1.0, 0, 3, -1, 1, "Crying: new tears at both eyes."),
    32: (1.0, 0, 4, 0, -1, "Crying: last pair of tears starts down."),
    36: (1.0, 0, 3, 0, 0, "The tears stop; the head lifts back to rest."),
    40: (1.0, 0, 2, 0, 0, "Facing us, still: the hold before the turn back."),
    44: (1.0, 0, 2, 0, 0, "Still facing us, eyes on the camera."),
    45: (0.85, -1, 2, 0, 0, "The bill starts to swing to our left."),
    46: (0.5, -2, 1, 0, 0, "Turning back: the bill points down-left, three-quarter head (film frame 46)."),
    47: (0.15, -1, 0, 0, 0, "Nearly back in profile, bill out to the left (film frame 47 is blurred mid-turn)."),
}
# crying frames between the head keys: drawn so the tears can be keyed every two frames
for f in (14, 18, 22, 26, 30, 34, 38):
    a = max(k for k in HEAD if k < f); b = min(k for k in HEAD if k > f); u = (f - a) / (b - a)
    HEAD[f] = tuple(HEAD[a][j] * (1 - u) + HEAD[b][j] * u for j in range(5)) + ("Crying: a tear frame, the head between its neighbours.",)
HEAD[14] = HEAD[14][:5] + ("Facing us; the eyes well up (no tear yet).",)
HEAD[38] = HEAD[38][:5] + ("The last tear lands; the head at rest.",)

# ---- tears: (name, track x, birth frame); each falls eye -> chest -> ground over 4-6 frames, keyed every 2
EYE_Y, CHEST_Y, GROUND_Y = 110, 160, 236
TEARS = [('tearL1', 203, 16), ('tearR1', 236, 16), ('tearL2', 204, 20), ('tearR2', 238, 22),
         ('tearL3', 202, 24), ('tearR3', 237, 28), ('tearL4', 204, 28), ('tearL5', 203, 32), ('tearR4', 236, 32)]
def tear_at(x0, b, f):
    k = (f - b) // 2   # 0 at the eye, 1 on the chest, 2 lower chest, 3 on the ground
    ys = [EYE_Y, CHEST_Y - 25, CHEST_Y + 30, GROUND_Y]
    if k < 0 or k > 3: return None
    xoff = [0, -2, -3, -3][k]
    return drop(x0 + xoff, ys[k], [1.2, 1.5, 1.5, 1.4][k])

for f, (t, dx, dy, bill, tilt, why) in sorted(HEAD.items()):
    S = blend(t, dx, dy, bill, tilt)
    ex = {}
    for nm, x0, b in TEARS:
        if f % 2 == 0:
            d = tear_at(x0, b, f)
            if d: ex[nm] = d
    if ex: why = why + " Tears: " + ", ".join(sorted(ex)) + "."
    json.dump({'why': why, 'strokes': [np.round(s, 1).tolist() for s in S], 'extra': ex},
              open(D / f'k{f:03d}.json', 'w'))
print(sorted(HEAD))
