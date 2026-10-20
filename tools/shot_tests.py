"""Run the shot tests on a puppet redraw (shots/<cat>-redraw/), the same battery as Giraffe Walks Past
where it applies, and write tests.json beside the shot.

usage: python3 tools/shot_tests.py <category> [...]

M2  style: the cast at each key, Quick, Draw!-simplified, against real doodles of the category
M3  mask fit: ink inside a GrabCut silhouette of the footage. GrabCut is seeded only by a box around
    the key (the agent's placement, enlarged 15%); the silhouette itself comes from the pixels.
    SAM was not available here; this is a weaker, partly circular stand-in and is marked so.
M4  planted contacts: world-space drift inside planted intervals (needs at least 4 intervals)
M5  proportions: each bone's on-screen length across frames, coefficient of variation
M6  smooth arcs: largest third difference of the first joint's path (px)
T3  strokes carried: every frame draws the same doodle strokes, so 1.0 by construction
B1  background held: the plate is drawn once, so 100% by construction
S2  sources: the cast names its Quick, Draw! key_id; the plate names its origin
S3  exposure sheet: one row per frame, keys marked
S6  source record: the batch's source.json fields
"""
import json, math, sys
from pathlib import Path
import numpy as np, cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from style_score import style

NEED = ['clip_id', 'source_id', 'start_seconds', 'end_seconds', 'shot_page_url', 'rights_statement']


def grabcut_fit(frame_path, strokes, W, H):
    img = cv2.imread(str(frame_path))
    pts = np.concatenate([np.array(s) for s in strokes if len(s)])
    x0, y0 = pts.min(0); x1, y1 = pts.max(0); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = (x1 - x0) * 1.15, (y1 - y0) * 1.15
    rx0, ry0 = int(max(1, cx - w / 2)), int(max(1, cy - h / 2)); rx1, ry1 = int(min(W - 2, cx + w / 2)), int(min(H - 2, cy + h / 2))
    if rx1 - rx0 < 8 or ry1 - ry0 < 8: return 0.0, None
    mask = np.zeros(img.shape[:2], np.uint8); bg = np.zeros((1, 65), np.float64); fg = np.zeros((1, 65), np.float64)
    cv2.grabCut(img, mask, (rx0, ry0, rx1 - rx0, ry1 - ry0), bg, fg, 5, cv2.GC_INIT_WITH_RECT)
    sil = np.isin(mask, [cv2.GC_FGD, cv2.GC_PR_FGD]).astype(np.uint8)
    sil = cv2.dilate(sil, np.ones((13, 13), np.uint8))
    ink = np.zeros_like(sil)
    for s in strokes:
        if len(s) > 1: cv2.polylines(ink, [np.round(np.array(s)).astype(np.int32)], False, 1, 2)
    inside = float((ink & sil).sum() / max(ink.sum(), 1))
    ys, xs = np.nonzero(cv2.erode(sil, np.ones((13, 13), np.uint8)))
    if not len(xs): return 0.0, sil
    a = (xs.min(), ys.min(), xs.max(), ys.max()); b = (x0, y0, x1, y1)
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy; uni = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return float(inside * inter / max(uni, 1)), sil


def run(cat):
    d = ROOT / 'shots' / f'{cat}-redraw'; S = json.load(open(d / 'shot.json')); rig = json.load(open(d / 'rig.json'))
    cast = S['cast']['frames']; keys = S['cast']['keys']; W, H = S['W'], S['H']; n = len(cast)
    out = []
    m2 = [style(cast[k], cat) for k in keys]
    out.append({'id': 'M2', 'value': round(float(np.mean(m2))), 'unit': 'percentile (Quick, Draw! simplification first)', 'ok': bool(np.mean(m2) >= 30), 'per_key': [round(x) for x in m2]})
    fits = [grabcut_fit(d / 'frames' / f'f{k:03d}.jpg', cast[k], W, H)[0] for k in keys]
    out.append({'id': 'M3', 'value': round(float(np.mean(fits)), 2), 'unit': 'fit to a GrabCut silhouette (not SAM)', 'ok': bool(np.mean(fits) >= 0.65 and min(fits) >= 0.45),
                'per_key': [round(x, 2) for x in fits], 'note': 'GrabCut seeded by a box around the agent-placed key; weaker than SAM and partly circular'})
    # M4: planted contacts in world space
    cam = S['camera']; J = S['joints']; planted = S['planted']
    intervals = []
    for j in rig.get('contacts', []):
        run_ = []
        for f in range(n):
            if j in planted[f]: run_.append(f)
            elif run_: intervals.append((j, run_)); run_ = []
        if run_: intervals.append((j, run_))
    drift = [max(math.dist(np.array(J[f][j]) - cam[f], np.array(J[r[0]][j]) - cam[r[0]]) for f in r) for j, r in intervals]
    if rig.get('contacts'):
        ok = len(intervals) >= 4 and max(drift or [99]) < 2
        out.append({'id': 'M4', 'value': round(max(drift), 2) if drift else 'no planted intervals', 'unit': f'px drift over {len(intervals)} planted intervals', 'ok': ok})
    else:
        out.append({'id': 'M4', 'value': 'not applicable', 'unit': 'nothing in this shot stands on the ground', 'ok': None})
    # M5: bone length stability on screen
    cv = {}
    for b, (a, c) in rig['bones'].items():
        L = np.array([math.dist(J[f][a], J[f][c]) for f in range(n)])
        cv[b] = float(L.std() / max(L.mean(), 1e-9))
    worst = max(cv, key=cv.get)
    out.append({'id': 'M5', 'value': round(100 * cv[worst], 1), 'unit': f'% variation (worst bone: {worst})', 'ok': bool(cv[worst] < 0.10), 'per_bone': {k: round(100 * v, 1) for k, v in cv.items()}})
    # M6: smoothness of the lead joint
    lead = list(rig['joints'])[0]; P = np.array([J[f][lead] for f in range(n)])
    jerk = float(np.abs(np.diff(P, n=3, axis=0)).max()) if n > 3 else 0.0
    out.append({'id': 'M6', 'value': round(jerk, 1), 'unit': f'px jerk ({lead})', 'ok': bool(jerk < 4)})
    out.append({'id': 'T3', 'value': '1.00', 'unit': 'same doodle strokes every frame', 'ok': True, 'note': 'by construction'})
    out.append({'id': 'B1', 'value': 100, 'unit': '% strokes held (plate drawn once)', 'ok': True, 'note': 'by construction'})
    out.append({'id': 'S2', 'value': f"quickdraw:{S['design']['key_id']}", 'unit': '', 'ok': True})
    out.append({'id': 'S3', 'value': f"{len(S['xsheet'])}/{n}", 'unit': 'frames', 'ok': len(S['xsheet']) == n})
    src = json.load(open(ROOT / f'batches/2026-10-20-selected-drawings/subjects/{cat}/source.json'))['source']
    miss = [k for k in NEED if not str(src.get(k, '')).strip()]
    out.append({'id': 'S6', 'value': 'complete' if not miss else 'missing ' + ', '.join(miss), 'unit': '', 'ok': not miss})
    old = {t['id']: t for t in json.load(open(d / 'tests.json'))} if (d / 'tests.json').exists() else {}
    keep = {i: old[i] for i in old if i in ('M1', 'J1', 'J4')}
    res = out + [keep[i] for i in ('M1', 'J1', 'J4') if i in keep]
    (d / 'tests.json').write_text(json.dumps(res, indent=1))
    print(f"{cat:11s} " + '  '.join(f"{t['id']}={t['value']}{'' if t['ok'] is None else (' ok' if t['ok'] else ' FAIL')}" for t in out if t['id'] in ('M2', 'M3', 'M4', 'M5', 'M6')))


if __name__ == '__main__':
    for c in sys.argv[1:]: run(c)
