"""How much the drawing jumps from frame to frame, the measure the critics keep naming ("broken at frame 5").
For each frame pair: shift of the drawing's centre, change of its size (RMS radius), both relative to the
drawing's size, after removing the camera for scenery-fixed comparisons is not needed (the character follows
the footage). Reports the worst step and the 95th percentile, next to the same numbers for Giraffe Walks Past.
usage: python3 tools/pops.py [slug ...]"""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent


def pops(frames):
    C, R = [], []
    for fr in frames:
        P = np.concatenate([np.array(s, float) for s in fr if len(s)]); c = P.mean(0); C.append(c); R.append(np.sqrt(((P - c) ** 2).sum(1).mean()))
    C, R = np.array(C), np.array(R); r = np.median(R)
    # step relative to the drawing's size, minus the steady part of the motion (a pan is fine, a jump is not)
    v = np.diff(C, axis=0); acc = np.linalg.norm(np.diff(v, axis=0), axis=1) / r if len(v) > 1 else np.zeros(1)
    ds = np.abs(np.diff(np.log(R)))
    return {'accel': round(float(acc.max()), 3), 'accel95': round(float(np.percentile(acc, 95)), 3), 'size_step': round(float(ds.max()), 3), 'size95': round(float(np.percentile(ds, 95)), 3)}


def run(slugs):
    g = json.load(open(ROOT / 'shots/giraffe-walks-past/shot.json')); base = pops(g['cast']['frames'])
    print(f"{'giraffe-walks-past':16s} {base}")
    out = {'giraffe-walks-past': base}
    for s in slugs:
        p = ROOT / 'shots' / f'{s}-gwp' / 'shot.json'
        if not p.exists(): continue
        S = json.load(open(p)); r = pops(S['cast']['frames']); out[s] = r
        flag = ' <-' if r['accel'] > 2 * base['accel'] or r['size_step'] > 2 * base['size_step'] + 0.02 else ''
        print(f'{s:16s} {r}{flag}')
    return out


if __name__ == '__main__':
    sl = sys.argv[1:] or sorted(p.parent.name[:-4] for p in ROOT.glob('shots/*-gwp/shot.json'))
    json.dump(run(sl), open(ROOT / 'data' / 'pops.json', 'w'), indent=1)
