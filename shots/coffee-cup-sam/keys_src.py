"""Key table for coffee-cup, written by eye from the frames: rim ellipse centre (x, y) in frame px, the angle phi
(degrees) of the doodle's left-to-right rim direction on screen (the body points 90 degrees clockwise from it),
rim opening and body length. Writes pose_agent_vN.json with the root points rimL, rimR placed by one similarity."""
import json, math, sys
S = 1.03; C0 = (100.0, 40.0)
K = {  # frame: (cx, cy, phi, rim, body)
 0: (168, 80, -90, 2.2, 0.2), 4: (192, 83, -90, 2.2, 0.25), 8: (140, 82, -78, 2.2, 0.5), 12: (153, 88, -75, 2.4, 0.6),
 16: (203, 80, -70, 2.4, 0.75), 20: (200, 45, -60, 2.2, 0.8), 24: (178, 62, -45, 2.0, 0.85), 28: (177, 80, -20, 1.6, 0.75),
 32: (152, 75, -30, 2.0, 0.6), 36: (142, 92, -35, 2.4, 0.5), 40: (102, 112, -35, 2.7, 0.35), 44: (158, 118, -35, 2.7, 0.3),
 46: (148, 118, -35, 2.7, 0.3), 49: (132, 115, -35, 2.7, 0.3)}
def place(cx, cy, phi, p):
    a = math.radians(phi); dx, dy = p[0] - C0[0], p[1] - C0[1]
    return [round(cx + S * (math.cos(a) * dx - math.sin(a) * dy), 1), round(cy + S * (math.sin(a) * dx + math.cos(a) * dy), 1)]
out = {}
for f, (cx, cy, phi, r, b) in sorted(K.items()):
    out[str(f)] = {'rimL': place(cx, cy, phi, (1, 58)), 'rimR': place(cx, cy, phi, (200, 48)), 'rim': r, 'body': b}
json.dump(out, open(sys.argv[1], 'w'), indent=1)
