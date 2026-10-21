"""Drawn keys for the sailboat, made from the rig drawing at each key frame by moving the doodle's own points:
the hull (S0 deck, S1 outline) is pressed down toward its keel line as the boat comes close and the camera sits
lower than its deck, and the sail (S2) and mast (S3) are enlarged about the mast foot and widened aft, so the
sail looms over the hull at the line. Same strokes, same points."""
import json, numpy as np
from pathlib import Path
R = Path('/home/claude/cartoon-archive'); D = R / 'shots/sailboat/drawn'
rig = json.load(open(R / 'shots/sailboat-gwp/rig_frames.json'))
# frame: (hull height kh, sail size ks, sail extra width aft kw, dx, dy, why)
K = {
 0:  (0.92, 1.00, 1.00, 0, 0, 'start: the barge is far off, a narrow boat seen bow-quarter, about a quarter of the frame wide, right of centre with its hull on the horizon'),
 16: (0.90, 1.03, 1.00, 0, 0, 'approach: the same narrow boat a little bigger, the masthead climbing toward the top edge'),
 32: (0.86, 1.06, 1.04, 0, 0, 'contact: the masthead touches the top edge of the frame; from here on the boat is too big for the frame'),
 42: (0.82, 1.10, 1.08, 0, 0, 'the sail head has left the top of the frame and the boat is still sliding left'),
 48: (0.77, 1.12, 1.12, 0, 0, 'extreme: the leftmost point of the drift; the barge stops sliding left and starts to swing its stern out to the right (anticipation of the line)'),
 54: (0.72, 1.14, 1.20, 0, 0, 'breakdown: the boom and stern swing out to the right, the boat lengthens as it turns its side to us'),
 60: (0.66, 1.16, 1.26, 0, 0, 'the line: the barge fills the frame, sail cut off by the top edge, stern and boom reaching the right edge'),
 66: (0.63, 1.17, 1.28, 0, 0, 'settle: the stern runs off the right edge, the hull keeps growing'),
 73: (0.60, 1.18, 1.30, 0, 0, 'end: the hull fills the lower half and the sail the upper right; the boat is passing out of frame to the right'),
}
CLEW = {42: 300, 48: 306, 54: 326, 60: 355, 66: 368, 73: 376}
for f, (kh, ks, kw, dx, dy, why) in K.items():
    S = [np.array(s, float) for s in rig[f]]
    bot = S[1][:, 1].max()
    for i in (0, 1): S[i][:, 1] = bot - (bot - S[i][:, 1]) * kh
    foot = S[3][5].copy()   # mast foot, on the deck line
    newfoot = np.array([foot[0], bot - (bot - foot[1]) * kh])
    for i in (2, 3):
        P = S[i] - foot; P *= ks
        if i == 2:
            cx = CLEW.get(f)   # widen or narrow aft (right of the mast) so the clew lands where the film's is
            k = kw if cx is None else (cx - newfoot[0]) / max(P[3, 0], 1e-6)
            P[:, 0] = np.where(P[:, 0] > 0, P[:, 0] * k, P[:, 0])
        S[i] = P + newfoot
    S = [s + [dx, dy] for s in S]
    old = json.load(open(D / f'k{f:03d}.json')) if (D / f'k{f:03d}.json').exists() else {}
    json.dump({'why': why, 'strokes': [np.round(s, 1).tolist() for s in S], 'extra': old.get('extra', {})}, open(D / f'k{f:03d}.json', 'w'))
print('keys', sorted(K))
