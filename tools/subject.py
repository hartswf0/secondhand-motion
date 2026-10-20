"""One subject through the Giraffe Walks Past line, step by step. Each subject is still done by hand; this
keeps track of where it is, runs the automatic steps, and makes the sheets the hand steps need.

usage:
  python3 tools/subject.py status [slug ...]       where every subject is (writes data/line.json)
  python3 tools/subject.py import <slug>           CI output -> shots/<slug>-sam/ (after tracking ran)
  python3 tools/subject.py first <slug> [every]    first-pass keys from the silhouettes -> pose_agent_v1.json
  python3 tools/subject.py sheets <slug>           doodle sheet, key grids (with rig and any generated keys)
  python3 tools/subject.py build <slug>            shot, tests, critic packet

Steps, and who does each:
  1 survey   CI      contact sheet of the whole clip, cut spikes, a bank of 40 real doodles (survey.yml)
  2 plan     agent   choose the continuous interval and one doodle; write shots/<slug>/plan.json
  3 track    CI      frames, SAM 2.1 masks, Depth Anything depth (add the slug to data/track-now.json)
  4 rig      agent   rigs/<slug>_spec.json from the numbered doodle sheet: root, joints, regions, spins
  5 keys     agent   first pass from the silhouettes, then corrected by eye on the grids
  6 scene    agent   rigs/<slug>_scene.json: Quick, Draw! scenery in boxes, planes with z from depth
  7 build    auto    shot.json, tests, critic packet, page
  8 critic   agent   a fresh blind critic per subject; repair the one gap named; repeat at most three times
"""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def state(slug):
    n = slug.replace('-', '_'); s = ROOT / 'shots'; r = ROOT / 'rigs'
    w1 = (ROOT / 'batches/2026-10-20-selected-drawings/subjects' / slug / 'source.json').exists()
    st = {
        'survey': w1 or (s / slug / 'survey' / 'sheet.jpg').exists() or (s / slug / 'keyplan.json').exists(),
        'plan': w1 or (s / slug / 'plan.json').exists() or (s / slug / 'keyplan.json').exists(),
        'track': (s / f'{slug}-sam' / 'masks.json').exists(),
        'rig': (r / f'{n}_spec.json').exists(),
        'keys': any((s / f'{slug}-sam').glob('pose_agent_v*.json')) or ('field' in json.load(open(r / f'{n}_spec.json')) if (r / f'{n}_spec.json').exists() else False),
        'scene': (r / f'{n}_scene.json').exists(),
        'build': (s / f'{slug}-gwp' / 'shot.json').exists(),
        'critic': any((s / f'{slug}-gwp' / 'reviews').glob('critic-*.json')) if (s / f'{slug}-gwp' / 'reviews').exists() else False}
    nxt = next((k for k, v in st.items() if not v), 'done')
    j4 = None
    if st['critic']:
        v = json.load(open(sorted((s / f'{slug}-gwp' / 'reviews').glob('critic-*.json'))[-1])); j4 = v.get('identity_verdict'), v.get('motion_reads'), v.get('follows_film')
    return {'slug': slug, 'steps': st, 'next': nxt, 'critic': j4}


def all_slugs():
    out = []
    for p in sorted((ROOT / 'rigs').glob('*_spec.json')):
        n = p.name[:-10]; out.append(n.replace('_', '-'))
    w3 = json.load(open(ROOT / 'data' / 'wave3.json'))['subjects'] if (ROOT / 'data' / 'wave3.json').exists() else []
    out += [x['slug'] for x in w3 if x['slug'] not in out and not x.get('rejected')]
    return [x for x in out if (ROOT / 'shots' / x).exists() or (ROOT / 'shots' / f'{x}-sam').exists()]


def main():
    cmd = sys.argv[1]; args = sys.argv[2:]
    if cmd == 'status':
        rows = [state(s) for s in (args or all_slugs())]
        for r in rows: print(f"{r['slug']:15s} next: {r['next']:7s} " + ' '.join(('x' if v else '.') for v in r['steps'].values()) + (f"  critic {r['critic']}" if r['critic'] else ''))
        if not args:
            json.dump(rows, open(ROOT / 'data' / 'line.json', 'w'), indent=1)
            names = list(rows[0]['steps'])
            md = ['# Production line', '',
                  'Every subject goes through the same eight steps, one subject at a time. CI does the survey and the tracking for a whole wave in one push; '
                  'the plan, rig, keys and scene are hand work per subject; the critic is a fresh blind agent per subject. '
                  'Written by `tools/subject.py status`.', '',
                  '| Subject | ' + ' | '.join(names) + ' | Next | Critic: identity, motion, follows film |', '|' + '---|' * (len(names) + 3)]
            for r in rows:
                link = f"[{r['slug']}](../pages/{r['slug']}-gwp.html)" if r['steps']['build'] else r['slug']
                md.append(f"| {link} | " + ' | '.join('done' if v else '' for v in r['steps'].values()) + f" | {r['next']} | {', '.join(r['critic']) if r['critic'] else ''} |")
            md += ['', '## The steps', '', '```', __doc__.split('Steps, and who does each:')[1].strip(), '```']
            (ROOT / 'docs' / 'production-line.md').write_text('\n'.join(md) + '\n')
    elif cmd == 'import':
        subprocess.run(['git', '-C', str(ROOT), 'fetch', '-q', '-f', 'origin', 'refs/heads/wave2-track/*:refs/remotes/origin/wave2-track/*'], check=True)
        subprocess.run([PY, str(ROOT / 'tools' / 'wave2_import.py'), args[0]], check=True)
    elif cmd == 'first':
        slug = args[0]; ev = args[1] if len(args) > 1 else '6'
        subprocess.run([PY, str(ROOT / 'rigs' / 'autoroot.py'), slug, ev], check=True)
        d = ROOT / 'shots' / f'{slug}-sam'; (d / 'pose_agent_v1.json').write_text((d / 'pose_auto.json').read_text())
        if not (d / 'rig_params.json').exists(): (d / 'rig_params.json').write_text('{}')
    elif cmd == 'sheets':
        slug = args[0]; d = ROOT / 'shots' / f'{slug}-sam'; out = ROOT / 'shots' / slug / 'sheets'; out.mkdir(parents=True, exist_ok=True)
        subprocess.run([PY, str(ROOT / 'tools' / 'doodle_sheet.py'), str(ROOT / 'shots' / slug / 'design.json'), str(out / 'doodle.png')], check=True)
        pv = sorted(d.glob('pose_agent_v*.json'), key=lambda p: int(p.stem.split('v')[-1]))
        keys = sorted(int(k) for k in json.load(open(pv[-1]))) if pv else json.load(open(d / 'clip.json'))['keys']
        extra = (['--pose', str(pv[-1]), '--rig', str(ROOT / 'rigs' / f"{slug.replace('-', '_')}.py")] if pv else [])
        tgt = ROOT / 'shots' / slug / 'keys' / 'traced.json'
        if tgt.exists(): extra += ['--target', str(tgt)]
        for i in range(0, len(keys), 6):
            subprocess.run([PY, str(ROOT / 'tools' / 'key_grid.py'), str(d), str(out / f'keys-{i // 6 + 1}.png'), *map(str, keys[i:i + 6]), *extra], check=True)
        print('sheets in', out)
    elif cmd == 'build':
        slug = args[0]; cat = json.load(open(ROOT / 'rigs' / f"{slug.replace('-', '_')}_spec.json"))['category']
        part = ROOT / 'data' / 'quickdraw' / f'{cat}.part'
        if not part.exists():   # the tests compare against real doodles of the category
            subprocess.run(['curl', '-sSf', '-r', '0-2500000', 'https://storage.googleapis.com/quickdraw_dataset/full/simplified/' + cat.replace(' ', '%20') + '.ndjson', '-o', str(part)], check=True)
        for c in (['gwp_build.py', slug], ['gwp_tests.py', slug], ['critic_packet.py', slug, '--suffix=gwp']):
            subprocess.run([PY, str(ROOT / 'tools' / c[0]), *c[1:]], check=True)


if __name__ == '__main__':
    main()
