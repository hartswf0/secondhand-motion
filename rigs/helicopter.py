"""Helicopter rig: the chosen doodle itself (rigs/helicopter_spec.json), bent by pose points. See template_rig.py.

The rotor is the doodle's own four blade lines (the left blade at the end of the mast stroke and strokes 2-4).
They turn together as one rotor seen from the side: each blade end travels round a flat ellipse in the rotor
plane (depth squash ROTOR_K), so a blade swings from long to short and back instead of standing up like a fan,
and no blade is ever drawn on top of another. Each blade keeps the doodler's length and starts at the angle round
the disc nearest the way the doodler drew it, so at spin 0 the rotor is the doodle's rotor flattened onto the disc.
"""
from pathlib import Path
import sys, math
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from template_rig import TemplateRig
_R = TemplateRig(Path(__file__).parent / 'helicopter_spec.json')
POINTS = _R.POINTS
ROTOR_K = 0.3   # depth squash of the rotor disc seen from the side
# (stroke, vertex of the blade's root, vertex of the blade's end) in the doodle
BLADES = [(1, 1, 2), (2, 0, 1), (3, 0, 1), (4, 0, 1)]


def _blades():
    S = _R.strokes; out = []
    for s, i0, i1 in BLADES:
        st = np.array(S[s][i0], float); v = np.array(S[s][i1], float) - st
        a0 = math.atan2(v[1] / ROTOR_K, v[0]); L = math.hypot(v[0], v[1])
        out.append((s, i0, i1, st, a0, L))
    return out


_BL = _blades()


def rotor_doodle(spin):
    """Blade end points in doodle space at a spin angle (radians)."""
    return {(s, i1): st + L * np.array([math.cos(a0 + spin), ROTOR_K * math.sin(a0 + spin)]) for s, i0, i1, st, a0, L in _BL}


def draw(pose, prm=None):
    spin = float(pose.get('spin', 0.0)); p0 = dict(pose); p0['spin'] = 0.0
    out = [list(map(list, s)) for s in _R.draw(p0, prm)]
    A = _R.sp['anchors']; a0, a1 = _R.sp['root']
    dm, dt = np.array(A[a0], float), np.array(A[a1], float); pm, pt = np.array(pose[a0], float), np.array(pose[a1], float)
    z = complex(*(pt - pm)) / complex(*(dt - dm))
    to_frame = lambda q: (lambda c: [pm[0] + c.real, pm[1] + c.imag])(z * complex(*(np.asarray(q, float) - dm)))
    if (prm or {}).get('wobble'): return out
    for (s, i1), q in rotor_doodle(spin).items():
        if i1 < len(out[s]): out[s][i1] = to_frame(q)
    return out
