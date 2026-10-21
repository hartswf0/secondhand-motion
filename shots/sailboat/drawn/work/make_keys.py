"""Drawn keys for the sailboat (v4 base: the doodle in its own facing, sail on the left of the mast, raised end
stroke of the hull on the right). Each key is the rig drawing at that frame with the hull (S0 deck, S1 outline)
pressed slightly toward its keel line, the same amount in every key, so the hull keeps the doodle's proportions
from the first frame to the last; the sail (S2) and doubled mast (S3) stay as the rig draws them. Same strokes,
same points."""
import json, numpy as np
from pathlib import Path
R = Path('/home/claude/cartoon-archive'); D = R / 'shots/sailboat/drawn'
rig = json.load(open(R / 'shots/sailboat-gwp/rig_frames.json'))
KH = 0.92
K = {
 0:  'start: the barge is far off, about a quarter of the frame wide, right of centre with its hull on the horizon',
 16: 'approach: the same boat a little bigger, the masthead climbing toward the top edge',
 32: 'contact: the masthead touches the top edge of the frame; from here on the boat is too big for the frame',
 42: 'the sail head has left the top of the frame and the boat is still sliding left',
 48: 'extreme: the leftmost point of the drift; the barge stops sliding left and starts back to the right (anticipation of the line)',
 54: 'breakdown: the boat starts back right and keeps growing',
 60: 'the line: the barge fills the frame, sail cut off by the top edge, the hull reaching toward the right edge',
 66: 'settle: the raised end of the hull runs off the right edge, the boat keeps growing',
 73: 'end: the hull fills the lower half; the boat is passing out of frame to the right',
}
for f, why in K.items():
    S = [np.array(s, float) for s in rig[f]]
    bot = S[1][:, 1].max(); foot = S[3][5].copy()
    for i in (0, 1): S[i][:, 1] = bot - (bot - S[i][:, 1]) * KH
    dy = (bot - (bot - foot[1]) * KH) - foot[1]
    for i in (2, 3): S[i][:, 1] += dy
    json.dump({'why': why, 'strokes': [np.round(s, 1).tolist() for s in S], 'extra': {}}, open(D / f'k{f:03d}.json', 'w'))
print('keys', sorted(K))
