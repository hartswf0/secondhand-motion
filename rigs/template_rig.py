"""A rig made from the chosen doodle itself. The doodle's own vertices and strokes are kept; every frame is
the same drawing, bent at a few joints, never a new drawing.

A rig spec (rigs/<cat>_spec.json) gives:
  strokes  the doodle's strokes, [[x,y],...] in Quick, Draw! 0-255 space; facing: -1 left, +1 right
  anchors  name -> [x,y] in doodle space; the pose gives the same names in frame pixels
  root     two anchor names; one similarity (shift, turn, scale) carries the whole doodle so that these
           two points land on the pose. It sets where the drawing is, how big, and its tilt, and keeps the
           doodle's own proportions.
  parts    {stroke, from, to, joint, aim:[a, b], stretch?, pin?}: after the root, vertices from..to turn
           about `joint` (an anchor, or with pin the vertex just before `from`) so that the doodle's a->b
           direction matches the pose's a->b direction. stretch (0..1, default 0) lets the part lengthen
           or shorten toward the pose's a->b length; 0 keeps the doodle's length. turn (0..1, default 1) applies
           that share of the turn, so a part keeps some of the doodle's own angle.
  spin (optional): the part also turns about its joint by pose[spin] radians, clockwise on screen
           (wheel spokes, rotor blades, sails).
  shift_by/shift (optional): vertices of the part move by pose[shift_by] x shift (doodle units) before
           placement: a jaw opening, a mouth.
  yaw (pose entry, -1..1) with spec front_regions [[x0,y0,x1,y1],...] in doodle space: a head turn; the
           features inside those boxes slide further than the outline.
  _face, _xscale (pose entries): force the facing, and narrow the drawing about its centre line (a flipbook
           turn: 1 -> 0.4, flip, 0.4 -> 1).
  fold/axis (optional): the part folds toward the axis line (two anchors) by pose[fold] (1 open, 0 shut),
           as wings close.
Params: wobble, seg (hand wobble on long segments; 0 keeps the doodle's lines exactly), seed.
"""
import json, math
import numpy as np


def _sim(src, dst):
    (a, b), (c, d) = np.array(src, float), np.array(dst, float)
    v, w = b - a, d - c; s = np.hypot(*w) / max(np.hypot(*v), 1e-6); r = math.atan2(w[1], w[0]) - math.atan2(v[1], v[0])
    R = s * np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
    return lambda p: (R @ (np.array(p, float) - a)) + c


class TemplateRig:
    def __init__(self, spec_path):
        sp = json.load(open(spec_path)); self.sp = sp
        self.strokes = [np.array(s, float) for s in sp['strokes']]; self.face = sp.get('facing', -1)
        self.POINTS = list(sp['anchors'])

    def expand(self, parts):
        """A part may name a region [x0, y0, x1, y1] of the doodle instead of a stroke and vertex range: it then
        covers every vertex inside that box not claimed by an earlier part. 'rest': true covers everything left."""
        if getattr(self, '_exp', None) is not None: return self._exp
        claimed = set(); out = []
        for p in parts:
            if 'region' in p or p.get('rest'):
                x0, y0, x1, y1 = p.get('region', [-1e9, -1e9, 1e9, 1e9])
                for si, st in enumerate(self.strokes):
                    run = []
                    for vi, (x, y) in enumerate(st):
                        ok = (si, vi) not in claimed and x0 <= x <= x1 and y0 <= y <= y1
                        if ok: run.append(vi); claimed.add((si, vi))
                        if (not ok or vi == len(st) - 1) and run:
                            q = {k: v for k, v in p.items() if k not in ('region', 'rest')}; q.update(stroke=si, **{'from': run[0], 'to': run[-1]}); out.append(q); run = []
            else:
                for vi in range(p['from'], p['to'] + 1): claimed.add((p['stroke'], vi))
                out.append(p)
        self._exp = out; return out

    def draw(self, pose, prm=None):
        prm = prm or {}; sp = self.sp
        a0, a1 = sp['root']
        face = 1 if pose[sp.get('face_from', ['nose', 'tail'])[0]][0] >= pose[sp.get('face_from', ['nose', 'tail'])[1]][0] else -1
        if '_face' in pose: face = 1 if pose['_face'] >= 0 else -1
        flip = face != self.face
        mir = lambda v: np.array([255 - v[0], v[1]], float) if flip else np.array(v, float)
        A = {k: mir(v) for k, v in sp['anchors'].items()}
        if '_scale' in pose:
            # size from the silhouette (pose['_scale'], doodle units -> px); direction from a0->a1, tilt limited
            tv = A[a1] - A[a0]; pv = np.array(pose[a1], float) - np.array(pose[a0], float)
            ta = math.atan2(tv[1], tv[0]); pa = math.atan2(pv[1], pv[0])
            lim = math.radians(sp.get('max_tilt', 30)); d = math.atan2(math.sin(pa - ta), math.cos(pa - ta))
            d = max(-lim, min(lim, d)); sc = pose['_scale']
            # foreshorten along the body axis: a side-view doodle on a turned body gets shorter, a stretched
            # body longer, within limits; across the axis the size stays the silhouette's
            lo, hi = sp.get('foreshorten', [0.5, 1.4])
            sl = min(max(np.hypot(*pv) / max(np.hypot(*tv), 1e-6), lo * sc), hi * sc)
            u = tv / max(np.hypot(*tv), 1e-6); Pm = np.outer(u, u); Q = np.eye(2) - Pm
            Rd = np.array([[math.cos(d), -math.sin(d)], [math.sin(d), math.cos(d)]])
            R0 = Rd @ (sl * Pm + sc * Q); o = np.array(pose[a0], float)
            root = lambda p, R0=R0, o=o, a=A[a0]: R0 @ (np.array(p, float) - a) + o
        else:
            r0 = _sim([A[a0], A[a1]], [pose[a0], pose[a1]]); m = sp.get('scale_mult', 1.0); o = np.array(pose[a0], float)
            root = (lambda p, r0=r0, m=m, o=o: o + m * (r0(p) - o)) if m != 1.0 else r0
        out = [[None] * len(s) for s in self.strokes]
        for part in self.expand(sp['parts']):
            s = part['stroke']
            if part.get('pin'):
                j = part['from'] - 1; piv = np.array(out[s][j], float)
            else:
                piv = root(A[part['joint']])
            a, b = part['aim']
            pa_ = np.array(pose[a], float) if a in pose else root(A[a])   # an aim point the pose does not give is
            pb_ = np.array(pose[b], float) if b in pose else root(A[b])   # where the root puts the doodle's own
            tv = root(A[b]) - root(A[a]); pv = pb_ - pa_
            ang = math.atan2(pv[1], pv[0]) - math.atan2(tv[1], tv[0])
            ang = math.atan2(math.sin(ang), math.cos(ang)) * part.get('turn', 1.0)   # turn: share of the turn applied
            if part.get('spin'): ang += (1 if not flip else -1) * float(pose.get(part['spin'], 0.0)) * (-1 if self.face < 0 else 1)
            k = 1.0 + part.get('stretch', 0) * (np.hypot(*pv) / max(np.hypot(*tv), 1e-6) - 1.0)
            R = k * np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
            fold = pose.get(part['fold'], 1.0) if part.get('fold') else None
            ax = (root(A[part['axis'][1]]) - root(A[part['axis'][0]])) if part.get('axis') else None
            for i in range(part['from'], part['to'] + 1):
                if out[s][i] is None:
                    v0 = np.array(self.strokes[s][i], float)
                    if part.get('shift_by'):   # e.g. a jaw: vertices move in doodle space by pose[shift_by] x shift
                        v0 = v0 + float(pose.get(part['shift_by'], 0.0)) * np.array(part['shift'], float)
                    q = root(mir(v0))
                    if fold is not None:   # fold toward the axis line: the across-axis offset times pose[fold]
                        o = root(A[part['axis'][0]]); u = ax / max(np.hypot(*ax), 1e-6); r = q - o; along = (r @ u) * u
                        q = o + along + (r - along) * fold
                    out[s][i] = (R @ (q - piv) + piv).tolist()
        if pose.get('yaw') and sp.get('front_regions'):
            # a head turning toward profile: the outline narrows a little, features on the face slide toward the
            # turn (more than the outline), so a frontal doodle turns without being redrawn
            allp = np.array([q for st in out for q in st if q is not None], float); cx = allp[:, 0].mean(); wd = np.ptp(allp[:, 0]); yv = float(pose['yaw'])
            inner = set()
            for x0, y0, x1, y1 in sp['front_regions']:
                for si, st in enumerate(self.strokes):
                    for vi, (x, y) in enumerate(st):
                        if x0 <= x <= x1 and y0 <= y <= y1: inner.add((si, vi))
            out = [[None if q is None else [cx + (q[0] - cx) * (1 - 0.25 * abs(yv)) + yv * wd * (0.15 if (si, vi) in inner else 0.04), q[1]]
                    for vi, q in enumerate(st)] for si, st in enumerate(out)]
        if '_xscale' in pose and abs(pose['_xscale']) < 0.999:
            # a flipbook turn: the drawing narrows toward its own centre line, flips facing, and widens again;
            # its height and every joint stay as drawn, so nothing comes apart mid-turn
            allp = np.array([q for st in out for q in st if q is not None], float); cx = allp[:, 0].mean(); k = max(abs(pose['_xscale']), 0.3)
            out = [[None if q is None else [cx + (q[0] - cx) * k, q[1]] for q in st] for st in out]
        res = []; rng = np.random.default_rng(prm.get('seed', 3)); seg = prm.get('seg', 0); wob = prm.get('wobble', 0)
        for st in out:
            st = [p for p in st if p is not None]
            if seg and wob:
                d = []
                for p, q in zip(st[:-1], st[1:]):
                    L = math.hypot(q[0] - p[0], q[1] - p[1]); n = max(1, int(L // seg))
                    nx, ny = -(q[1] - p[1]) / (L or 1), (q[0] - p[0]) / (L or 1); bow = rng.uniform(-1, 1) * wob
                    for i in range(n):
                        t = i / n; m = math.sin(math.pi * t) * bow
                        d.append([p[0] + (q[0] - p[0]) * t + nx * m, p[1] + (q[1] - p[1]) * t + ny * m])
                d.append(st[-1]); st = d
            res.append([[round(x, 1), round(y, 1)] for x, y in st])
        return res
