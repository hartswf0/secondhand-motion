"""Key table for coffee-cup, written by eye from the frames: rim ellipse centre (x, y) in frame px, the angle phi
(degrees) of the doodle's left-to-right rim direction on screen (the body points 90 degrees clockwise from it),
rim opening and body length. Writes pose_agent_vN.json with the root points rimL, rimR placed by one similarity."""
import json, math, sys
S = 1.03; C0 = (100.5, 53.0)
K = {  # frame: (cx, cy, phi, rim, body)
 0: (172, 80, -90, 2.7, 0.12), 4: (196, 83, -90, 2.7, 0.15), 8: (140, 82, -78, 2.2, 0.5), 12: (153, 88, -75, 2.4, 0.6),
 16: (203, 80, -70, 2.3, 0.65), 20: (200, 45, -60, 2.0, 0.7), 24: (180, 62, -18, 1.8, 0.7), 28: (177, 80, -20, 1.5, 0.85),
 32: (152, 75, -25, 1.7, 0.62), 36: (142, 92, -30, 2.1, 0.5), 40: (102, 112, -35, 2.7, 0.35), 44: (158, 118, -35, 2.7, 0.3),
 46: (148, 118, -35, 2.7, 0.3), 49: (132, 115, -35, 2.7, 0.3)}
def place(cx, cy, phi, p):
    a = math.radians(phi); dx, dy = p[0] - C0[0], p[1] - C0[1]
    return [round(cx + S * (math.cos(a) * dx - math.sin(a) * dy), 1), round(cy + S * (math.sin(a) * dx + math.cos(a) * dy), 1)]
out = {}
for f, (cx, cy, phi, r, b) in sorted(K.items()):
    a = math.radians(phi); n = (-math.sin(a), math.cos(a)); cx, cy = cx + 13 * r * S * n[0], cy + 13 * r * S * n[1]
    out[str(f)] = {'rimL': place(cx, cy, phi, (1, 58)), 'rimR': place(cx, cy, phi, (200, 48)), 'rim': r, 'body': b, 'ticks': round(1 + 0.3 * (r - 1), 2)}
json.dump(out, open(sys.argv[1], 'w'), indent=1)
