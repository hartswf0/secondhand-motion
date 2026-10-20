"""Secondhand Motion brand mark: a wire coat hanger that walks.

The mark is drawn the way the project draws everything: as strokes, in four held keys.
Writes assets/brand/*.svg and the favicon set. Run from the repository root:
    python3 tools/brand.py
PNG sizes are rendered with Playwright's Chromium (already used for page checks).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets' / 'brand'

INK, TAG, PAPER = '#161412', '#EF9F3A', '#F6EFE3'

# 64 x 64 drawing. Hook and hanger are fixed; legs change per key.
HOOK = 'M27.5 13.2C27.6 9.4 30.6 7 34 7.4c3.2.4 5.2 3.2 4.6 6.2-.5 2.6-2.8 3.9-5.1 4.4-1.2.3-1.5 1-1.5 2.2V22'
HANGER = 'M32 22 7.5 35.5c-1.6.9-1 3 .8 3h47.4c1.8 0 2.4-2.1.8-3L32 22Z'
# each key: two legs, each [hip, knee, ankle, toe]
KEYS = [
    [[[28, 38.5], [24, 49], [17, 58.5], [23.5, 59.5]], [[36, 38.5], [41, 49], [46, 58.5], [52.5, 58]]],          # contact
    [[[28, 38.5], [28.5, 49], [29, 59.5], [35.5, 59.5]], [[36, 38.5], [42, 47], [37, 54], [43.5, 53.5]]],        # passing
    [[[28, 38.5], [33, 49], [38, 58.5], [44.5, 58]], [[36, 38.5], [31.5, 49], [25, 58.5], [31.5, 59.5]]],        # contact, other leg
    [[[28, 38.5], [34, 47], [29, 54], [35.5, 53.5]], [[36, 38.5], [36, 49], [36, 59.5], [42.5, 59.5]]],          # passing, other leg
]


def legs(key):
    return ''.join(f'M{h[0]} {h[1]}L{k[0]} {k[1]}L{a[0]} {a[1]}L{t[0]} {t[1]}' for h, k, a, t in key)


# ---- gaits: every lot's hanger wears its pants a different way ---------------------------------
# A key gives each leg as knee, ankle, toe relative to its hip, plus a body move (dx, dy, tilt degrees).
# Hips sit at (28, 38.5) and (36, 38.5); the floor is y = 59.5, about 21 below the hips.
HIPS = [(28, 38.5), (36, 38.5)]
STAND = [(0, 10.5), (0, 21), (6, 21)]
G = {
    'walk':      None,  # the mark's own four keys, filled in below
    'strut':     [([(-2, 10), (-6, 20), (0, 21)], [(6, 6), (3, 14), (9, 13)], (0, -1, 0)), ([(0, 10.5), (0, 21), (6, 21)], [(4, 9), (6, 18), (12, 18)], (0, 0, 0)),
                  ([(6, 6), (3, 14), (9, 13)], [(-2, 10), (-6, 20), (0, 21)], (0, -1, 0)), ([(4, 9), (6, 18), (12, 18)], [(0, 10.5), (0, 21), (6, 21)], (0, 0, 0))],
    'moonwalk':  [([(1, 10.5), (1, 21), (7, 21)], [(3, 10), (-2, 19), (3, 21)], (0, 0, -5)), ([(0, 10.5), (-3, 21), (3, 21)], [(3, 10), (0, 19), (5, 21)], (0, 0, -5)),
                  ([(3, 10), (-2, 19), (3, 21)], [(1, 10.5), (1, 21), (7, 21)], (0, 0, -5)), ([(3, 10), (0, 19), (5, 21)], [(0, 10.5), (-3, 21), (3, 21)], (0, 0, -5))],
    'tiptoe':    [([(-1, 10), (-2, 19), (-1, 23)], [(2, 10), (3, 19), (4, 23)], (0, -2, 0)), ([(1, 9), (2, 17), (3, 21)], [(2, 10), (3, 19), (4, 23)], (0, -2.5, 0)),
                  ([(2, 10), (3, 19), (4, 23)], [(-1, 10), (-2, 19), (-1, 23)], (0, -2, 0)), ([(2, 10), (3, 19), (4, 23)], [(1, 9), (2, 17), (3, 21)], (0, -2.5, 0))],
    'cancan':    [(STAND, [(8, -2), (16, -5), (18, -9)], (0, 0, -6)), (STAND, STAND, (0, 0, 0)),
                  ([(-8, -2), (-16, -5), (-18, -9)], STAND, (0, 0, 6)), (STAND, STAND, (0, 0, 0))],
    'hop':       [([(5, 9), (0, 18), (6, 18)], [(5, 9), (0, 18), (6, 18)], (0, 3, 0)), ([(1, 10), (0, 20), (5, 21)], [(1, 10), (0, 20), (5, 21)], (0, -6, 0)),
                  ([(2, 9.5), (0, 19), (3, 22)], [(2, 9.5), (0, 19), (3, 22)], (0, -8, 0)), ([(3, 10), (0, 20), (6, 20)], [(3, 10), (0, 20), (6, 20)], (0, -2, 0))],
    'goose step': [(STAND, [(8, 7), (16, 14), (19, 9)], (0, 0, -2)), (STAND, STAND, (0, 0, 0)),
                  ([(8, 7), (16, 14), (19, 9)], STAND, (0, 0, -2)), (STAND, STAND, (0, 0, 0))],
    'shuffle':   [([(3, 8), (-1, 18), (5, 18)], [(4, 8), (1, 18), (7, 18)], (0, 3, 0)), ([(4, 8), (1, 18), (7, 18)], [(3, 8), (-1, 18), (5, 18)], (0, 3, 0))],
    'sprint':    [([(-4, 9), (-14, 14), (-17, 11)], [(9, 4), (6, 13), (11, 15)], (0, -2, 8)), ([(4, 6), (-3, 11), (1, 14)], [(1, 10), (-1, 20), (5, 20)], (0, 1, 8)),
                  ([(9, 4), (6, 13), (11, 15)], [(-4, 9), (-14, 14), (-17, 11)], (0, -2, 8)), ([(1, 10), (-1, 20), (5, 20)], [(4, 6), (-3, 11), (1, 14)], (0, 1, 8))],
    'jelly':     [([(-5, 10), (0, 21), (5, 21)], [(5, 10), (0, 21), (5, 21)], (0, 0, -3)), ([(4, 10), (0, 21), (5, 21)], [(-4, 10), (0, 21), (5, 21)], (0, 0, 3))],
    'splits':    [(STAND, STAND, (0, 0, 0)), ([(-8, 8.5), (-16, 17), (-21, 17)], [(8, 8.5), (16, 17), (21, 17)], (0, 4, 0)),
                  ([(-10, 5), (-20, 11), (-25, 11)], [(10, 5), (20, 11), (25, 11)], (0, 10, 0)), ([(-8, 8.5), (-16, 17), (-21, 17)], [(8, 8.5), (16, 17), (21, 17)], (0, 4, 0))],
    'heel click': [(STAND, STAND, (0, 0, 0)), ([(-5, 9), (4, 18), (-1, 20)], [(5, 9), (-4, 18), (1, 20)], (0, -7, 0)),
                  ([(-5, 9), (4, 18), (-1, 20)], [(5, 9), (-4, 18), (1, 20)], (0, -5, 0)), (STAND, STAND, (0, 0, 0))],
    'skip':      [(STAND, [(6, 6), (3, 14), (9, 13)], (0, -2, 0)), ([(-2, 10), (-5, 19), (0, 21)], [(6, 6), (4, 14), (9, 14)], (0, -5, 0)),
                  ([(6, 6), (3, 14), (9, 13)], STAND, (0, -2, 0)), ([(6, 6), (4, 14), (9, 14)], [(-2, 10), (-5, 19), (0, 21)], (0, -5, 0))],
    'sit':       [([(9, 3), (14, 12), (19, 10)], [(10, 2), (16, 10), (21, 8)], (0, 8, -4)), ([(9, 3), (14, 12), (19, 10)], [(10, 2), (17, 9), (21, 5)], (0, 8, -4))],
}


def gait_keys(name):
    if name == 'walk':
        return [{'legs': legs(k), 'move': [0, 0, 0]} for k in KEYS]
    out = []
    for L, R, mv in G[name]:
        dx, dy, rot = mv
        key = [[(hx + dx, hy + dy)] + [(hx + dx + a, hy + dy + b) for a, b in rel] for (hx, hy), rel in zip(HIPS, (L, R))]
        out.append({'legs': legs([[list(map(lambda v: round(v, 2), p)) for p in leg] for leg in key]), 'move': [dx, dy, rot]})
    return out


GAIT_NAMES = list(G)


def gaits():
    return {n: gait_keys(n) for n in GAIT_NAMES}


def mark(key=0, ink=INK, bg=None, sw=3.6, size=64, pad=0):
    v = f'{-pad} {-pad} {64 + 2 * pad} {64 + 2 * pad}'
    back = f'<rect x="{-pad}" y="{-pad}" width="{64 + 2 * pad}" height="{64 + 2 * pad}" rx="{14 + pad}" fill="{bg}"/>' if bg else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{v}" width="{size}" height="{size}">{back}'
            f'<g fill="none" stroke="{ink}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="{HOOK}"/><path d="{HANGER}"/><path d="{legs(KEYS[key])}"/></g></svg>')


def data():
    """What pages need to draw and animate the mark inline."""
    return {'hook': HOOK, 'hanger': HANGER, 'legs': [legs(k) for k in KEYS], 'gaits': gaits(), 'order': GAIT_NAMES}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'mark.svg').write_text(mark())
    (OUT / 'mark-light.svg').write_text(mark(ink=PAPER))
    for i in range(4): (OUT / f'walk-{i}.svg').write_text(mark(i))
    fav = mark(0, ink=INK, bg=TAG, sw=5.2, pad=1)
    (ROOT / 'favicon.svg').write_text(fav)
    (OUT / 'brand.json').write_text(json.dumps(data(), indent=1))
    render(fav)
    print('wrote', sorted(p.name for p in OUT.iterdir()))


def render(fav):
    from playwright.sync_api import sync_playwright
    card = f'''<html><body style="margin:0;width:1200px;height:630px;background:{PAPER};display:flex;align-items:center;gap:56px;padding:0 90px;box-sizing:border-box;font-family:Arial Black,Arial,sans-serif">
    <div style="width:300px;height:300px;flex:none">{mark(0, sw=3.2, size=300)}</div>
    <div><div style="font:800 92px/0.95 Arial Black,Arial,sans-serif;color:{INK};letter-spacing:-2px">Secondhand<br>Motion</div>
    <div style="font:500 30px/1.3 Arial,sans-serif;color:#6B6259;margin-top:26px;max-width:640px">Archive film, redrawn as moving Quick, Draw! doodles.</div>
    <div style="margin-top:26px;display:inline-block;background:{TAG};color:{INK};font:700 22px monospace;padding:6px 14px;border-radius:4px">hartswf0.github.io/secondhand-motion</div></div></body></html>'''
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, size in [('favicon-32.png', 32), ('favicon-192.png', 192), ('apple-touch-icon.png', 180)]:
            pg = b.new_page(viewport={'width': size, 'height': size})
            pg.set_content(f'<html><body style="margin:0;background:transparent">{fav.replace("width=\"64\" height=\"64\"", f"width=\"{size}\" height=\"{size}\"")}</body></html>')
            pg.screenshot(path=str(ROOT / name if name != 'favicon-192.png' else OUT / name), omit_background=True)
        pg = b.new_page(viewport={'width': 1200, 'height': 630})
        pg.set_content(card); pg.screenshot(path=str(OUT / 'social-card.png'))
        b.close()


if __name__ == '__main__':
    main()
