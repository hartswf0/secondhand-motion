"""Giraffe doodle rig: pose keypoints -> Quick, Draw!-style strokes.

Pose (frame pixel coords):
  head   top of head (ossicone base)     nose  muzzle tip
  nb     neck base, top (withers side)   chest neck base, front/bottom
  rump   top of hindquarters             tailroot  where tail leaves body
  belly_f, belly_h  underside above front/hind legs
  hooves list of 2-4 [x,y] (front first)
Params (the reward tunes these):
  neck_w   neck thickness as fraction of neck length
  leg_w    leg thickness in px (0 = single-line legs)
  spots    number of spot circles
  ossicones, tail  booleans
"""
import json, math, sys
import numpy as np

def lerp(a, b, t):
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]

def norm(v):
    n = math.hypot(*v) or 1
    return [v[0] / n, v[1] / n]

def draw(pose, prm):
    st = []
    head, nose, nb, chest = pose['head'], pose['nose'], pose['nb'], pose['chest']
    rump, belly_f, belly_h = pose['rump'], pose['belly_f'], pose['belly_h']
    hooves = pose['hooves']
    lw = prm.get('leg_w', 4)
    # one continuous outline: rump -> back -> neck back edge -> head -> nose -> neck front -> chest
    #   -> front legs -> belly -> hind legs -> rump
    mz = prm.get('muzzle', 0)
    if mz:
        d = norm([nose[0] - head[0], nose[1] - head[1]]); n = [-d[1], d[0]]
        if n[1] < 0: n = [-n[0], -n[1]]          # perpendicular pointing down
        L = math.hypot(nose[0] - head[0], nose[1] - head[1])
        brow = [head[0] + d[0] * L * 0.15 - n[0] * mz * 0.3, head[1] + d[1] * L * 0.15 - n[1] * mz * 0.3]
        muzzle_b = [nose[0] + n[0] * mz, nose[1] + n[1] * mz]
        jaw = [head[0] + d[0] * L * 0.35 + n[0] * mz * 1.5, head[1] + d[1] * L * 0.35 + n[1] * mz * 1.5]
        outline = [rump, nb, head, brow, nose, muzzle_b, jaw, chest]
    else:
        outline = [rump, nb, head, nose]
        jaw = lerp(nose, head, 0.45)
        jaw = [jaw[0] + (chest[0] - head[0]) * 0.06, jaw[1] + (chest[1] - head[1]) * 0.12]
        outline += [jaw, chest]
    legs_front = [h for h in hooves[:2]]
    legs_hind = [h for h in hooves[2:]]
    face = 1 if nose[0] >= rump[0] else -1
    knees = pose.get('knees', {})
    bend = prm.get('bend', 6)
    def leg_path(top_from, top_to, hoof, idx=None, front=True):
        mid = lerp(top_from, top_to, 0.5)
        if lw <= 0:
            k = knees.get(str(idx))
            if k is None:
                k = lerp(mid, hoof, 0.5)
                k = [k[0] + face * bend * (1 if front else -1), k[1]]
            return [mid, k, hoof, k, mid]
        return [[mid[0] - lw, mid[1]], [hoof[0] - lw * 0.7, hoof[1]], [hoof[0] + lw * 0.7, hoof[1]], [mid[0] + lw, mid[1]]]
    underside = [chest] + [belly_f] + [belly_h] + [pose.get('thigh', rump)]
    # interleave legs along the underside, in x order matching body direction
    pts = [chest]
    tops = []
    for i, h in enumerate(legs_front):
        a = lerp(chest, belly_f, 0.25 + 0.5 * i)
        tops.append((a, h))
    for i, h in enumerate(legs_hind):
        a = lerp(belly_h, pose.get('thigh', rump), 0.25 + 0.5 * i)
        tops.append((a, h))
    for i, (a, h) in enumerate(tops):
        pts += leg_path(a, a, h, i, i < len(legs_front))
    pts += [pose.get('thigh', rump), rump]
    outline = outline[:-1] + pts
    st.append(outline)
    if prm.get('ossicones', True):
        up = norm([head[0] - nose[0] * 0.0 - head[0] + 0, -1])
        d = norm([nose[0] - head[0], nose[1] - head[1]])
        L = math.hypot(nose[0] - head[0], nose[1] - head[1]) * 0.45
        base1 = lerp(head, nose, 0.05); base2 = lerp(head, nose, 0.3)
        for b in (base1, base2):
            st.append([b, [b[0] - d[0] * 0.2 * L, b[1] - L]])
    if prm.get('tail', True):
        tr = pose.get('tailroot', rump)
        back = norm([rump[0] - nb[0], rump[1] - nb[1]])
        tl = prm.get('tail_len', 26)
        st.append([tr, [tr[0] + back[0] * 6, tr[1] + tl * 0.6], [tr[0] + back[0] * 9, tr[1] + tl]])
        if prm.get('tuft'):
            e = [tr[0] + back[0] * 9, tr[1] + tl]
            st += [[[e[0], e[1]], [e[0] - 3, e[1] + 6]], [[e[0], e[1]], [e[0], e[1] + 7]], [[e[0], e[1]], [e[0] + 3, e[1] + 6]]]
    n = prm.get('spots', 0)
    if n:
        rng = np.random.default_rng(prm.get('seed', 1))
        body_c = lerp(lerp(nb, rump, 0.5), lerp(belly_f, belly_h, 0.5), 0.5)
        r = abs(belly_f[1] - nb[1]) * 0.12 + 1.5
        for _ in range(n):
            cx = body_c[0] + rng.uniform(-0.35, 0.35) * abs(rump[0] - nb[0])
            cy = body_c[1] + rng.uniform(-0.25, 0.25) * abs(belly_f[1] - nb[1])
            st.append([[cx + r * math.cos(t), cy + r * math.sin(t)] for t in np.linspace(0, 2 * math.pi, 7)])
    out = []
    rng2 = np.random.default_rng(prm.get('seed', 1) + 7)
    seg = prm.get('seg', 0)      # max segment length in frame px (0 = no subdivision)
    wob = prm.get('wobble', 0)   # hand wobble in px
    for s in st:
        if seg and len(s) > 1:
            d = []
            for a, b in zip(s[:-1], s[1:]):
                L = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(1, int(L // seg))
                nx, ny = -(b[1] - a[1]) / (L or 1), (b[0] - a[0]) / (L or 1)
                bow = rng2.uniform(-1, 1) * wob
                for i in range(n):
                    t = i / n; k = math.sin(math.pi * t) * bow
                    d.append([a[0] + (b[0] - a[0]) * t + nx * k, a[1] + (b[1] - a[1]) * t + ny * k])
            d.append(s[-1]); s = d
        out.append([[round(x, 1), round(y, 1)] for x, y in s])
    return out

if __name__ == '__main__':
    poses = json.load(open(sys.argv[1]))
    prm = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    print(json.dumps({k: draw(p, prm) for k, p in poses.items()}))
