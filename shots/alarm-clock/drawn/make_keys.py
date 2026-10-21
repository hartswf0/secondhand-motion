"""Writes the drawn keys k###.json for alarm-clock from per-key measurements of the film.
The clock is the doodle's own strokes. Facing us it is the doodle's one round circle with its dot, two diagonal
hands, two bells and two feet. As the hand turns it, the case circle narrows into the face rim seen at an angle
(width/height = cos(turn)); the dot and the two diagonal hands are kept and narrowed less than the rim so they stay
readable; the bells slide toward the middle of the drum's top; the right foot slides back under the drum.
Extra stroke case_back: the drum's back edge, a partial arc on the right that grows from nothing (lying on the
rim) as the clock turns and shrinks back to nothing when it faces us (the doodle draws only the face).
Extra stroke hand: the woman's hand that turns the clock, ten points in the same order in every key."""
import json, math
from pathlib import Path
D = Path(__file__).resolve().parent
spec = json.load(open(D.parents[2] / 'rigs' / 'alarm_clock_spec.json'))
ST = spec['strokes']
CY, RY, DEPTH, SY = 141, 57, 96, 57 / 90.0   # face centre y, face half-height, drum depth, doodle-to-frame scale


def clock(cx, rx, tilt=0.0):
    c = rx / RY; s = math.sqrt(max(0, 1 - c * c))
    vis = min(1.0, max(0.0, (0.85 - c) / 0.55))     # how much of the drum's side shows: 0 facing us, 1 side-on
    sx = rx / 99.0; hx = SY * max(c, 0.55)            # rim narrows fully; dot and hands narrow less

    def put(x, y, dx=0.0):
        return [round(cx + x - y * tilt + dx, 1), round(CY + y, 1)]
    out = [[put((p[0] - 100) * sx, (p[1] - 136) * SY) for p in ST[0]]]
    out += [[put((p[0] - 100) * hx, (p[1] - 136) * SY) for p in ST[i]] for i in (1, 2, 3)]
    xm = cx + 0.45 * DEPTH * s * vis                 # middle of the drum's top
    for i, off in ((4, -58), (5, 52)):               # bells: shape kept, centres bunch toward xm as it turns
        bx0 = sum(p[0] for p in ST[i]) / len(ST[i])
        tx = xm - cx + off * SY * max(c, 0.42)
        out.append([put(tx + (p[0] - bx0) * SY, (p[1] - 136) * SY) for p in ST[i]])
    out.append([put((p[0] - 100) * sx, (p[1] - 136) * SY) for p in ST[6]])
    out.append([put((p[0] - 100) * sx, (p[1] - 136) * SY, 0.30 * DEPTH * s * vis) for p in ST[7]])
    # case_back: partial arc of the drum's back edge
    rb = rx + (max(rx, 26) - rx) * vis
    backR = cx + rx + DEPTH * s * vis
    bx = backR - rb; A = 12 + 68 * vis
    arc = [[bx + rb * math.cos(math.radians(a)), RY * math.sin(math.radians(a))] for a in [-A + 2 * A * k / 6 for k in range(7)]]
    top = [cx - cx + 0.3 * rx + (arc[0][0] - cx - 0.3 * rx) * (1 - 0.7 * vis), arc[0][1] + (-RY + 1 - arc[0][1]) * vis]
    bot = [0.55 * rx + (arc[-1][0] - cx - 0.55 * rx) * (1 - 0.7 * vis), arc[-1][1] + (RY - 2 - arc[-1][1]) * vis]
    back = [put(*top)] + [put(x - cx, y) for x, y in arc] + [put(*bot)]
    return out, back


def sh(h, dx=0, dy=0): return [[x + dx, y + dy] for x, y in h]


H34 = [[-40, 150], [8, 138], [22, 128], [38, 126], [48, 132], [46, 142], [36, 156], [32, 172], [4, 186], [-40, 192]]
# hand points, same order every key: arm top at edge, wrist top, knuckle, fingertip top, fingertip end,
# fingertip under, palm, heel, under-arm, arm bottom at edge
KEYS = {
 0:  (172, 52, 0.00, [[0,72],[95,52],[128,26],[186,14],[204,26],[190,34],[152,44],[150,66],[92,84],[0,108]],
      "The hand has hold of the clock's top; the clock faces us. Start pose."),
 3:  (166, 44, 0.00, [[0,74],[100,50],[134,24],[190,22],[206,36],[192,42],[160,48],[152,70],[96,90],[0,116]],
      "The hand starts to turn the clock: the face narrows and the side begins to show. Start of the turn away."),
 6:  (156, 30, 0.04, [[0,96],[110,62],[148,38],[214,40],[230,54],[216,60],[180,58],[160,80],[100,106],[0,136]],
      "Mid turn away, fastest change: face half as wide, bells sliding together over the drum."),
 10: (146, 19, 0.06, [[0,116],[118,72],[148,52],[196,52],[204,62],[192,68],[176,68],[160,90],[108,122],[0,160]],
      "The turn away arrives: face edge-on at the left, the drum's side toward us. Extreme."),
 14: (141, 16, 0.08, [[0,118],[116,74],[140,56],[172,58],[178,66],[170,72],[160,74],[156,94],[108,124],[0,162]],
      "Held side-on, face a sliver, leaning a little under the hand. Extreme held."),
 18: (140, 16, 0.07, sh([[0,118],[116,74],[140,56],[172,58],[178,66],[170,72],[160,74],[156,94],[108,124],[0,162]], 0, -2),
      "Still side-on; the hand holds it there. Hold."),
 22: (138, 21, 0.04, [[0,114],[114,72],[138,54],[166,56],[172,64],[164,70],[156,74],[158,96],[108,126],[0,162]],
      "The face starts to come back: first widening. End of the hold."),
 24: (142, 28, 0.02, [[0,120],[108,82],[130,64],[164,64],[172,72],[162,78],[150,82],[158,106],[108,132],[0,170]],
      "Anticipation of the turn back: the hand moves down onto the face's left edge, face still narrow."),
 25: (158, 42, 0.00, [[0,126],[98,96],[124,84],[150,90],[160,100],[152,108],[144,118],[138,136],[100,150],[0,182]],
      "The hand swings the face back round toward us: one fast frame, as in the film."),
 26: (166, 50, 0.00, [[0,134],[80,110],[110,94],[136,92],[148,100],[142,108],[134,118],[130,138],[90,152],[0,186]],
      "THE LINE: the clock faces us again, one round face, the hand pressed to its left side."),
 28: (168, 52, 0.00, [[0,138],[70,118],[98,82],[112,52],[124,46],[132,54],[128,84],[132,124],[96,152],[0,184]],
      "Contact released: the fingers lift off the clock; the clock stands on its own, settled."),
 30: (168, 52, 0.00, [[0,136],[56,120],[80,86],[92,58],[104,52],[112,60],[110,90],[114,128],[80,154],[0,182]],
      "The open hand draws back to the left, arm shortening; breakdown so the withdrawal is continuous."),
 31: (168, 52, 0.00, [[0,132],[44,118],[62,84],[76,58],[88,52],[96,60],[96,90],[100,128],[70,152],[0,180]],
      "The open hand keeps pulling back to the left; the clock holds."),
 34: (168, 52, 0.00, H34, "The hand drops out at the left edge; the clock holds."),
 36: (168, 52, 0.00, sh(H34, -66, 2), "The hand has left the frame at the left; the clock alone, facing us."),
 37: (168, 52, 0.00, sh(H34, -66, 2), "End: the clock stands alone; the hand is kept just outside the frame so it does not blink out."),
}

for f, (cx, rx, tilt, hand, why) in KEYS.items():
    strokes, back = clock(cx, rx, tilt)
    json.dump({'why': why, 'strokes': strokes, 'extra': {'case_back': back, 'hand': hand}}, open(D / f'k{f:03d}.json', 'w'))
json.dump({'line': 26, 'line_why': "The clock's face swings back round to face us under the woman's hand (frames 24 to 26), after being held side-on from frame 10 to 22.",
           'holds': [[28, 37]]}, open(D / 'xsheet.json', 'w'), indent=1)
print('wrote', sorted(KEYS))
