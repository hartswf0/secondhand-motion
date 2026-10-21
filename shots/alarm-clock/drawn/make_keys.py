"""Writes the drawn keys k###.json for alarm-clock from per-key measurements of the film.
The clock is the doodle's own strokes: the case circle becomes the face rim seen at an angle (narrowed by
cos(turn) = rx/ry), the dot and hands are narrowed with it, the bells slide toward the middle of the drum's top,
the right foot slides back under the drum. One extra stroke, case_back, is the drum's back edge (the doodle draws
only the face); one extra stroke, hand, is the woman's hand that turns the clock."""
import json, math
from pathlib import Path
D = Path(__file__).resolve().parent
spec = json.load(open(D.parents[2] / 'rigs' / 'alarm_clock_spec.json'))
ST = spec['strokes']
CY, RY, DEPTH, SY = 141, 57, 96, 57 / 90.0   # face centre y, face half-height, drum depth, doodle-to-frame scale

def clock(cx, rx, tilt=0.0):
    c = rx / RY; s = math.sqrt(max(0, 1 - c * c))
    sx = rx / 99.0
    def face(p, dx=0.0):
        x, y = (p[0] - 100) * sx, (p[1] - 136) * SY
        # tilt: lean the clock about the face centre (positive leans top to the right)
        x, y = x + y * -tilt, y
        return [round(cx + x + dx, 1), round(CY + y, 1)]
    out = [[face(p) for p in ST[i]] for i in range(4)]
    xm = cx + 0.45 * DEPTH * s                           # middle of the drum's top
    for i, off in ((4, -58), (5, 52)):                     # bells: shape kept, centres bunch toward xm
        bx0 = sum(p[0] for p in ST[i]) / len(ST[i])
        tx = xm + off * SY * max(c, 0.42)
        out.append([[round(tx + (p[0] - bx0) * SY - (p[1] - 136) * SY * tilt, 1), round(CY + (p[1] - 136) * SY, 1)] for p in ST[i]])
    out.append([face(p) for p in ST[6]])
    out.append([face(p, 0.30 * DEPTH * s) for p in ST[7]])
    backR = cx + DEPTH * s + rx; rb = max(rx, 26); bx = backR - rb; mid = (cx + bx) / 2
    back = [[cx + 0.3 * rx, CY - RY + 1], [mid, CY - RY - 3], [bx, CY - RY - 1]]
    back += [[bx + rb * math.cos(math.radians(a)), CY + RY * 0.98 * math.sin(math.radians(a))] for a in (-55, -25, 2, 30, 58)]
    back += [[bx, CY + RY - 1], [mid, CY + RY + 1], [cx + 0.55 * rx, CY + RY - 2]]
    back = [[round(x - (y - CY) * tilt, 1), round(y, 1)] for x, y in back]
    return out, back

# frame: (face centre x, face half-width, tilt, hand points, why)
KEYS = {
 0:  (162, 38, 0.00, [[0,72],[95,52],[128,24],[198,12],[204,22],[152,42],[152,66],[92,84],[0,108]],
      "The hand has hold of the clock's top; the face is turned partly to the left. Start pose."),
 3:  (160, 33, 0.00, [[0,74],[100,50],[134,22],[205,22],[208,32],[160,46],[152,70],[96,90],[0,116]],
      "The hand starts to turn the clock: the face narrows. Start of the turn away."),
 6:  (153, 28, 0.04, [[0,96],[110,62],[148,36],[232,40],[234,50],[180,56],[160,80],[100,106],[0,136]],
      "Mid turn away, fastest change: face half as wide, bells sliding together over the drum."),
 10: (146, 19, 0.06, [[0,116],[118,72],[148,52],[200,52],[202,62],[176,66],[160,90],[108,122],[0,160]],
      "The turn away arrives: face edge-on at the left, the drum's back toward us. Extreme."),
 14: (141, 16, 0.08, [[0,118],[116,74],[140,56],[176,58],[176,68],[160,72],[156,94],[108,124],[0,162]],
      "Held side-on, face a sliver, leaning a little under the hand. Extreme held."),
 18: (140, 16, 0.07, [[0,116],[116,72],[140,54],[176,56],[176,66],[160,70],[156,92],[108,122],[0,160]],
      "Still side-on; the hand holds it there. Hold."),
 22: (138, 21, 0.04, [[0,114],[114,72],[138,54],[170,56],[170,66],[158,72],[158,96],[108,126],[0,162]],
      "The face starts to come back: first widening. End of the hold."),
 24: (140, 27, 0.02, [[0,120],[108,82],[130,64],[170,64],[172,74],[150,80],[158,106],[108,132],[0,170]],
      "Anticipation of the turn back: the hand moves down onto the face's left edge, face still narrow."),
 25: (150, 38, 0.00, [[0,126],[98,96],[124,84],[164,98],[164,108],[150,116],[146,134],[100,150],[0,182]],
      "The hand swings the face back round toward us: one fast frame, as in the film."),
 26: (155, 43, 0.00, [[0,134],[80,110],[110,94],[150,92],[152,102],[130,112],[140,140],[90,152],[0,186]],
      "THE LINE: the face is back toward us, round again, the hand pressed to its left side."),
 28: (156, 44, 0.00, [[0,136],[74,116],[100,74],[116,44],[132,46],[130,80],[140,122],[108,152],[0,186]],
      "Contact released: the fingers lift off the clock; the clock stands on its own, settled."),
 31: (156, 44, 0.00, [[0,132],[48,116],[66,78],[82,52],[98,52],[100,86],[108,126],[78,152],[0,180]],
      "The open hand pulls back to the left; the clock holds."),
 34: (156, 44, 0.00, [[-40,150],[8,138],[24,128],[46,132],[46,142],[34,156],[32,172],[4,186],[-40,192]],
      "The hand drops out at the left edge; the clock holds."),
 36: (156, 44, 0.00, [[-140,150],[-92,138],[-76,128],[-54,132],[-54,142],[-66,156],[-68,172],[-96,186],[-140,192]],
      "The hand is gone; the clock alone, face turned partly to the left, as at the end of the film."),
}

for f, (cx, rx, tilt, hand, why) in KEYS.items():
    strokes, back = clock(cx, rx, tilt)
    json.dump({'why': why, 'strokes': strokes, 'extra': {'case_back': back, 'hand': hand}}, open(D / f'k{f:03d}.json', 'w'))
json.dump({'line': 26, 'line_why': "The clock's face swings back round to face us under the woman's hand (frames 24 to 26), after being held side-on from frame 10 to 22.",
           'holds': [[28, 37]]}, open(D / 'xsheet.json', 'w'), indent=1)
print('wrote', sorted(KEYS))
