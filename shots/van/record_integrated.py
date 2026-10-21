"""Preserve complete candidates and append independent review evidence.

python shots/<subject>/record_integrated.py --proposal 1
python shots/<subject>/record_integrated.py --review 1
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

FOLDER = Path(__file__).resolve().parent
OUT = FOLDER/'integrated'
REPO = FOLDER.parents[1]
SLUG = FOLDER.name
sys.path.insert(0, str(REPO/'tools'))
import integrated_batch as engine

spec = importlib.util.spec_from_file_location('repair_loop', REPO/'batches/2026-10-20-selected-drawings/loop.py')
loop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loop)


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')


def entries():
    path = FOLDER/'ledger.jsonl'
    if not path.exists():
        loop.init_ledger(path)
    with path.open() as handle:
        return loop.read_ledger(handle)


def snapshot(n):
    target = OUT/'revisions'/f'v{n}'
    assert not target.exists(), f'Revision already preserved: {target}'
    target.mkdir(parents=True)
    for path in OUT.iterdir():
        if path.name == 'revisions' or path.name.startswith('.') or path.name == 'freeze.json':
            continue
        if path.is_dir():
            shutil.copytree(path, target/path.name)
        else:
            shutil.copy2(path, target/path.name)
    return target


def result(raw, name):
    aliases = {
        'identity': ['original_doodle_identity_bar_met', 'identity_bar_met'],
        'pose': ['source_framing_pose_bar_met'],
    }
    for key in aliases[name]:
        if key in raw:
            return raw[key] is True
    raise ValueError(f'Review missing explicit {name} verdict')


def record(n, reviewed):
    old = entries()
    revision = f'{SLUG}-integrated-v{n}'+('' if reviewed else '-proposal')
    if any(row['input']['revision'] == revision for row in old):
        return
    cfg = engine.read(OUT/'config.json')
    base = OUT/'revisions'/cfg.get('evidence_snapshot', f'v{n}')
    if not reviewed:
        base = snapshot(n)
    assert base.exists()
    checks = engine.read(base/'assembly-checks.json')
    source = engine.read(base/'source.json')
    review_path = OUT/f'review-v{n}.json'
    review = engine.read(review_path) if reviewed else {}
    identity = result(review, 'identity') if reviewed else 'unknown'
    pose = result(review, 'pose') if reviewed else 'unknown'
    still = reviewed and identity and pose
    protected = review.get('must_not_be_lost', [])
    if isinstance(protected, str):
        protected = [protected]
    if reviewed:
        shutil.copy2(review_path, base/review_path.name)
    ref = str(base.relative_to(FOLDER))+'/'
    trace = checks['trace_fidelity']
    raw = {
        'revision': revision,
        'parent': old[-1]['input']['revision'] if old else None,
        'observation_refs': [ref+'source.json', ref+'source-contact-sheet.jpg', ref+'design.json'],
        'evidence_refs': [str(review_path.relative_to(FOLDER)) if reviewed else ref+'assembly-checks.json'],
        'action': {'type': 'change_layer' if n == 1 else 'redraw_key',
                   'details': ('Independent sampled-still verdict for preserved candidate. ' if reviewed else 'Preserve complete source-paired candidate before independent critique. ')+engine.read(base/'config.json').get('repair_details', 'Source-observed native vector input frozen; held background/camera kept separate.')},
        'before_refs': ['integrated/input/design.png'] if n == 1 else [f'integrated/revisions/v{n-1}/shot.json'],
        'after_refs': [ref+'shot.json', ref+'comparison.mp4'],
        'source': {'identity': source['clip_id'], 'interval': {'start': source['start_seconds'], 'end': source['end_seconds'], 'unit': 'seconds'}},
        'claims': ['drawing', 'motion'],
        'source_event_preserved': 'unknown' if pose is True else pose,
        'drawing_identity_preserved': identity,
        'train_eligible': False,
        'measured_tests': [
            {'name': 'complete_decode', 'status': 'pass', 'constraint': True, 'value': checks['rendered_frames'], 'unit': 'frames', 'evidence_refs': [ref+'video-validation.json']},
            {'name': 'character_trace', 'status': 'pass' if trace['pass'] else 'fail', 'constraint': True, 'value': trace['min_recall'], 'unit': 'minimum recall', 'evidence_refs': [ref+'traced.json']},
            {'name': 'native_point_topology', 'status': 'pass' if checks['native_topology'] else 'fail', 'constraint': True},
            {'name': 'audited_final_native_SAM_fit', 'status': 'unknown', 'constraint': True},
            {'name': 'recognition_classifier', 'status': 'unknown', 'constraint': True},
            {'name': 'independently_verified_contacts', 'status': 'fail', 'constraint': True, 'value': 0, 'unit': 'verified planted intervals; at least four required'},
            {'name': 'independent_normal_speed_playback', 'status': 'unknown', 'constraint': True},
        ],
        'critic': {'scope': ['sampled_source_pose', 'native_doodle_identity_stills'] if reviewed else [],
                   'verdict': 'bar_met' if still else 'bar_not_met' if reviewed else 'uncertain',
                   'gap': (review.get('most_important_gap') or 'No sampled-still gap identified; normal-speed motion remains unapproved.'),
                   'protected_strengths': protected, 'independent': reviewed},
    }
    decision = loop.record(raw, FOLDER/'ledger.jsonl')
    print(revision, decision['decision']['status'])
    update(review if reviewed else None, n)


def update(review, n):
    shot = engine.read(OUT/'shot.json')
    checks = engine.read(OUT/'assembly-checks.json')
    identity = result(review, 'identity') if review else None
    pose = result(review, 'pose') if review else None
    still = bool(review and identity and pose)
    gap = (review.get('most_important_gap') or 'No sampled-still gap identified.') if review else 'Independent sampled-still review pending.'
    note = (f'Fresh still review v{n}: native identity '+('met' if identity else 'not met')+'; source framing/pose '+('met' if pose else 'not met')+'. ' if review else '')+gap+' Recognition classifier, audited final mask fit, four verified contacts and actual normal-speed playback remain unrun or unmet. No training ran.'
    shot.update(status='assembled_stills_pass_motion_gates_unmet' if still else 'assembled_review_gaps' if review else 'assembled_candidate_review_pending',
                review_status='still_pass_motion_unapproved' if still else 'still_gap_motion_unapproved' if review else 'review_pending',
                review_note=note, motion_approved=False, train_eligible=False, training_ran=False)
    if review:
        checks['independent_still_review'] = {'original_doodle_identity_bar_met': identity, 'source_framing_pose_bar_met': pose, 'round': n, 'evidence': f'review-v{n}.json'}
    checks['ledger_entries'] = len(entries())
    write(OUT/'shot.json', shot)
    write(OUT/'assembly-checks.json', checks)
    cfg = engine.read(OUT/'config.json')
    cfg['review_note'] = note
    write(OUT/'config.json', cfg)
    engine.build_page(OUT, shot, cfg)
    trace = checks['trace_fidelity']
    tests = [{'id': i, 'value': 'not run', 'unit': '', 'ok': None} for i in ['M1', 'M2', 'M2b', 'M5', 'M6', 'J1', 'J2', 'J3']]
    tests += [
        {'id': 'J4', 'value': {'original_doodle_identity_bar_met': identity, 'source_framing_pose_bar_met': pose, 'review': f'review-v{n}.json' if review else None}, 'unit': 'sampled stills only', 'ok': still if review else None},
        {'id': 'T1', 'value': trace, 'unit': 'fraction; recall>=.98 and all pieces retained', 'ok': trace['pass']},
        {'id': 'T3', 'value': checks['native_topology'], 'unit': 'native stroke IDs and original point counts retained', 'ok': checks['native_topology']},
        {'id': 'B1', 'value': checks['background_strokes_unchanged_fraction'], 'unit': checks['background_gate_scope'], 'ok': checks['held_background_geometry']},
        {'id': 'M3', 'value': checks['mask_fit'], 'unit': 'final native silhouette fit not measured', 'ok': None},
        {'id': 'M4', 'value': 0, 'unit': 'verified planted intervals; minimum4', 'ok': False},
        {'id': 'S1', 'value': 'Frozen source-observed camera and existing depth planes retained; final depth ordering independently unreviewed', 'unit': '', 'ok': None},
        {'id': 'S2', 'value': 'Native Quick, Draw! key '+str(shot['design']['key_id'])+'; extras and scenery sources preserved in compatibility/timeline', 'unit': '', 'ok': True},
        {'id': 'S3', 'value': {'frames': shot['frame_count'], 'keys': shot['keys'], 'source_time_every_frame': True}, 'unit': '', 'ok': True},
        {'id': 'S4', 'value': 'Offline links/script checked separately; actual390px browser interaction unrun', 'unit': '', 'ok': None},
        {'id': 'S5', 'value': 'Native closed-contour paper fills only; no source-mask cel. Depth/occlusion quality unreviewed', 'unit': '', 'ok': None},
        {'id': 'S6', 'value': 'Source IDs, interval, URLs, raw SHA and reported rights retained; Quick, Draw! CC BY4.0', 'unit': '', 'ok': True},
        {'id': 'S7', 'value': len(entries()), 'unit': 'verified hash-linked append-only ledger entries', 'ok': True},
    ]
    write(FOLDER/'tests.json', tests)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--proposal', type=int)
    choice.add_argument('--review', type=int)
    args = parser.parse_args()
    n = args.review or args.proposal
    assert 1 <= n <= 3
    record(n, args.review is not None)
