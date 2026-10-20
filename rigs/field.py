"""Field rig, for subjects that are a field of marks rather than one body (rain, a storm's surf).
The chosen doodle's own strokes are the marks; each frame moves them, so every frame is still the doodle's
drawing, repeated. Motion comes from the footage where it can be measured, and is labelled procedural where not.

spec['field'] = {
  'layers': [{'scale': px per doodle unit, 'tile': [w, h] px, 'velocity': [vx, vy] px/frame or 'measured',
              'band': [y0, y1] px (where the layer lives), 'jitter': px}],
  'measure_band': [y0, y1]   (for velocity 'measured': phase correlation of that band of the footage, frame to frame)
}
"""
import json, math
from pathlib import Path
import numpy as np, cv2


def measured_flow(d, n, band):
    g = [cv2.cvtColor(cv2.imread(str(Path(d) / 'frames' / f'f{f:03d}.jpg')), cv2.COLOR_BGR2GRAY).astype(np.float32)[band[0]:band[1]] for f in range(n)]
    win = cv2.createHanningWindow(g[0].shape[::-1], cv2.CV_32F); v = [[0.0, 0.0]]
    for i in range(1, n):
        (dx, dy), r = cv2.phaseCorrelate(g[i - 1], g[i], win)
        v.append([float(np.clip(dx, -20, 20)), float(np.clip(dy, -20, 20))] if r > 0.05 else v[-1])
    v = np.array(v); k = np.ones(5) / 5
    return np.c_[np.convolve(v[:, 0], k, 'same'), np.convolve(v[:, 1], k, 'same')]


def frames(d, spec, n, W, H):
    F = spec['field']; strokes = [np.array(s, float) for s in spec['strokes']]
    flow = measured_flow(d, n, F['measure_band']) if any(L['velocity'] == 'measured' for L in F['layers']) else None
    out = [[] for _ in range(n)]; rng = np.random.default_rng(7)
    for L in F['layers']:
        tw, th = L['tile']; sc = L['scale']; y0, y1 = L['band']
        cols = int(math.ceil(W / tw)) + 1; rows = int(math.ceil((y1 - y0) / th)) + 1
        offs = [(c * tw + rng.uniform(-L.get('jitter', 0), L.get('jitter', 0)), r * th + rng.uniform(-L.get('jitter', 0), L.get('jitter', 0))) for c in range(cols) for r in range(rows)]
        pos = np.zeros(2)
        for f in range(n):
            v = flow[f] * L.get('flow_gain', 1.0) + np.array(L.get('drift', [0, 0])) if L['velocity'] == 'measured' else np.array(L['velocity'], float)
            pos = pos + (v if f else 0)
            for ox, oy in offs:
                x = (ox + pos[0]) % (cols * tw) - tw; y = (oy + pos[1]) % (rows * th) - th + y0
                for s in strokes:
                    q = s * sc + [x, y]
                    if q[:, 1].max() < y0 - 4 or q[:, 1].min() > y1 + 4 or q[:, 0].max() < -4 or q[:, 0].min() > W + 4: continue
                    out[f].append(np.round(q, 1).tolist())
    return out
