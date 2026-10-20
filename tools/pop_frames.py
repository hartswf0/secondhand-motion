"""Where a shot jumps: the frames with the largest size step and centre acceleration, and the keys around them.
usage: python3 tools/pop_frames.py <slug>"""
import json, sys
import numpy as np
s = sys.argv[1]; S = json.load(open(f'shots/{s}-gwp/shot.json')); keys = S['cast']['keys']
C, R = [], []
for fr in S['cast']['frames']:
    P = np.concatenate([np.array(q, float) for q in fr if len(q)]); c = P.mean(0); C.append(c); R.append(np.sqrt(((P - c) ** 2).sum(1).mean()))
C, R = np.array(C), np.array(R); r = np.median(R)
acc = np.linalg.norm(np.diff(C, 2, axis=0), axis=1) / r; ds = np.diff(np.log(R))
print(s, 'n', len(R), 'keys', keys)
print('size steps', [(int(i), int(i + 1), round(float(ds[i]), 3)) for i in np.argsort(-np.abs(ds))[:5]])
print('accel     ', [(int(i + 1), round(float(acc[i]), 3)) for i in np.argsort(-acc)[:5]])
print('radius', [int(x) for x in R])
