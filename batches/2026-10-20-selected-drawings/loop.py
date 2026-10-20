#!/usr/bin/env python3
"""Append-only GPT tool-use search ledger; no policy training or scalar reward."""
import argparse
import copy
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile

ACTIONS = {'redraw_key', 'add_key', 'retime', 'repair_tracking', 'change_layer', 'reject_source'}
VERDICTS = {'bar_met', 'bar_not_met', 'uncertain'}
ZERO = '0' * 64


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def refs(value, name):
    require(isinstance(value, list) and value and all(isinstance(x, str) and x.strip() for x in value), name + ' must contain nonempty reference strings')


def truth(value):
    return value is True or value is False or value == 'unknown'


def normalize(raw):
    require(isinstance(raw, dict), 'input must be an object')
    data = copy.deepcopy(raw)
    allowed = {'revision', 'parent', 'observation_refs', 'evidence_refs', 'action', 'before_refs', 'after_refs', 'source', 'measured_tests', 'critic', 'claims', 'source_event_preserved', 'drawing_identity_preserved', 'train_eligible', 'runtime_cost'}
    require(not (set(data) - allowed), 'unknown input fields: ' + ', '.join(sorted(set(data) - allowed)))
    require(isinstance(data.get('revision'), str) and data['revision'].strip(), 'revision required')
    require('parent' in data and (data['parent'] is None or isinstance(data['parent'], str) and data['parent'].strip()), 'parent must be null or a revision')
    for name in ('observation_refs', 'evidence_refs', 'before_refs', 'after_refs'):
        refs(data.get(name), name)
    action = data.get('action')
    require(isinstance(action, dict) and action.get('type') in ACTIONS, 'invalid action type')
    require(not (set(action) - {'type', 'details'}), 'unknown action field')
    require('details' not in action or isinstance(action['details'], str), 'action details must be text')
    source = data.get('source')
    require(isinstance(source, dict) and isinstance(source.get('identity'), str) and source['identity'].strip(), 'source identity required')
    require(set(source) == {'identity', 'interval'}, 'source requires identity and interval only')
    interval = source.get('interval')
    require(isinstance(interval, dict) and set(interval) == {'start', 'end', 'unit'}, 'source interval requires start/end/unit')
    require(all(type(interval[k]) in (int, float) and math.isfinite(interval[k]) for k in ('start', 'end')), 'interval must be finite numbers')
    require(interval['end'] > interval['start'] >= 0 and interval['unit'] in ('seconds', 'frames'), 'invalid source interval')
    for name in ('source_event_preserved', 'drawing_identity_preserved'):
        data.setdefault(name, 'unknown')
        require(truth(data[name]), name + ' must be true, false, or unknown')
    data.setdefault('claims', ['motion'])
    require(isinstance(data['claims'], list) and data['claims'] and all(x in ('motion', 'drawing') for x in data['claims']), 'claims must contain motion and/or drawing')
    data.setdefault('train_eligible', False)
    require(type(data['train_eligible']) is bool, 'train_eligible must be boolean')
    data.setdefault('measured_tests', [])
    require(isinstance(data['measured_tests'], list), 'measured_tests must be an array')
    for test in data['measured_tests']:
        require(isinstance(test, dict) and set(test) <= {'name', 'status', 'constraint', 'value', 'unit', 'metric', 'evidence_refs'}, 'invalid measured test fields')
        require(isinstance(test.get('name'), str) and test['name'].strip(), 'test name required')
        require(test.get('status') in ('pass', 'fail', 'unknown') and type(test.get('constraint')) is bool, 'test needs status and constraint boolean')
        if 'value' in test:
            require(type(test['value']) in (int, float) and math.isfinite(test['value']), 'test value must be finite number')
            require(isinstance(test.get('unit'), str) and test['unit'].strip(), 'numeric measurements need units')
        if 'evidence_refs' in test:
            refs(test['evidence_refs'], 'test evidence_refs')
    critic = data.get('critic')
    require(isinstance(critic, dict) and set(critic) <= {'scope', 'verdict', 'gap', 'protected_strengths', 'independent', 'compared_playback'}, 'invalid critic fields')
    require(critic.get('verdict') in VERDICTS, 'critic verdict required')
    require(isinstance(critic.get('scope'), list) and all(isinstance(x, str) and x.strip() for x in critic['scope']), 'critic scope required')
    require(isinstance(critic.get('gap'), str), 'critic gap text required')
    require(isinstance(critic.get('protected_strengths'), list) and all(isinstance(x, str) for x in critic['protected_strengths']), 'protected_strengths array required')
    critic.setdefault('independent', False)
    require(type(critic['independent']) is bool, 'critic independent must be boolean')
    if 'compared_playback' in critic:
        comparison = critic['compared_playback']
        require(isinstance(comparison, dict) and set(comparison) == {'before_ref', 'after_ref', 'source_ref'}, 'compared_playback requires before/after/source references')
        require(all(isinstance(x, str) and x.strip() for x in comparison.values()), 'comparison references must be nonempty')
        require(comparison['before_ref'] != comparison['after_ref'], 'comparison must reference distinct playbacks')
    if 'runtime_cost' in data:
        cost = data['runtime_cost']
        require(isinstance(cost, dict) and set(cost) == {'value', 'unit'}, 'runtime_cost requires value and unit')
        require(type(cost['value']) in (int, float) and math.isfinite(cost['value']) and cost['value'] >= 0, 'runtime_cost must be nonnegative')
        require(isinstance(cost['unit'], str) and cost['unit'].strip(), 'runtime_cost unit required')
    return data


def evaluate(data):
    reasons = []
    failed = [t['name'] for t in data['measured_tests'] if t['constraint'] and t['status'] == 'fail']
    unknown = [t['name'] for t in data['measured_tests'] if t['constraint'] and t['status'] == 'unknown']
    for key in ('source_event_preserved', 'drawing_identity_preserved'):
        if data[key] is False:
            reasons.append(key + '=false')
    reasons.extend('constraint_failed:' + name for name in failed)
    if data['action']['type'] == 'reject_source':
        reasons.append('source_rejected')
    hard_failure = bool(reasons)
    critic = data['critic']
    if not hard_failure:
        for key in ('source_event_preserved', 'drawing_identity_preserved'):
            if data[key] != True:
                reasons.append(key + '=unknown')
        reasons.extend('constraint_unknown:' + name for name in unknown)
        if critic['verdict'] != 'bar_met':
            reasons.append('primary_quality_bar_not_met')
        if not critic['independent']:
            reasons.append('independent_critic_required')
        if 'motion' in data['claims']:
            if 'playback' not in critic['scope']:
                reasons.append('playback_scope_required')
            if not critic.get('compared_playback'):
                reasons.append('independent_compared_playback_required')
    status = 'rejected' if hard_failure else ('milestone_needs_review' if reasons else 'accepted')
    return {'status': status, 'reasons': reasons, 'preference_constraint_vector': {
        'critic_verdict': critic['verdict'], 'critic_scope': critic['scope'],
        'independent_critic': critic['independent'],
        'compared_playback': critic.get('compared_playback'),
        'source_event_preserved': data['source_event_preserved'],
        'drawing_identity_preserved': data['drawing_identity_preserved'],
        'failed_constraints': failed, 'unknown_constraints': unknown,
        'runtime_cost': data.get('runtime_cost'),
    }, 'train_eligible': data['train_eligible'] and status == 'accepted'}


def read_ledger(handle):
    handle.seek(0)
    entries, revisions = [], set()
    for line in handle:
        require(line.strip() and line.endswith('\n'), 'blank or incomplete ledger line')
        entry = json.loads(line)
        require(set(entry) == {'sequence', 'previous_hash', 'input', 'decision', 'id'}, 'invalid ledger entry')
        require(entry['sequence'] == len(entries) + 1, 'sequence mismatch')
        require(entry['previous_hash'] == (entries[-1]['id'] if entries else ZERO), 'hash chain broken')
        require(entry['id'] == digest({k: v for k, v in entry.items() if k != 'id'}), 'entry hash mismatch')
        data = normalize(entry['input'])
        require(data == entry['input'] and entry['decision'] == evaluate(data), 'noncanonical input or decision mismatch')
        require(data['revision'] not in revisions, 'duplicate revision')
        require(data['parent'] is None or data['parent'] in revisions, 'missing parent')
        revisions.add(data['revision'])
        entries.append(entry)
    return entries


def init_ledger(path):
    with open(path, 'x', encoding='utf-8'):
        pass
    return {'ledger': str(path), 'initialized': True}


def record(raw, path):
    data = normalize(raw)
    with open(path, 'r+', encoding='utf-8') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        entries = read_ledger(handle)
        revisions = {e['input']['revision'] for e in entries}
        require(data['revision'] not in revisions, 'duplicate revision refused')
        require(data['parent'] is None or data['parent'] in revisions, 'missing parent refused')
        payload = {k: v for k, v in data.items() if k not in ('revision', 'parent')}
        require(all(payload != {k: v for k, v in e['input'].items() if k not in ('revision', 'parent')} for e in entries), 'duplicate candidate payload refused')
        entry = {'sequence': len(entries) + 1, 'previous_hash': entries[-1]['id'] if entries else ZERO, 'input': data, 'decision': evaluate(data)}
        entry['id'] = digest(entry)
        handle.seek(0, 2)
        handle.write(canonical(entry) + '\n')
        handle.flush()
        os.fsync(handle.fileno())
    return entry


def select(path):
    with open(path, encoding='utf-8') as handle:
        fcntl.flock(handle, fcntl.LOCK_SH)
        entries = read_ledger(handle)
    accepted = [e for e in entries if e['decision']['status'] == 'accepted']
    return {'selection_rule': 'latest recorded candidate that clears all gates; no artistic ranking',
            'selected_revision': accepted[-1]['input']['revision'] if accepted else None,
            'selected_id': accepted[-1]['id'] if accepted else None,
            'candidates': [{'revision': e['input']['revision'], 'parent': e['input']['parent'], **e['decision']} for e in entries]}


def fixture(name):
    return {'revision': name, 'parent': None, 'observation_refs': ['fixture://observation/' + name], 'evidence_refs': ['fixture://evidence/' + name],
            'action': {'type': 'redraw_key', 'details': 'Synthetic gate test; no artwork inspected.'},
            'before_refs': ['fixture://before/' + name], 'after_refs': ['fixture://after/' + name],
            'source': {'identity': 'synthetic-source', 'interval': {'start': 0, 'end': 2, 'unit': 'seconds'}},
            'claims': ['motion'], 'measured_tests': [], 'source_event_preserved': True, 'drawing_identity_preserved': True,
            'critic': {'scope': ['drawing', 'playback', 'source_comparison'], 'verdict': 'bar_met', 'gap': '', 'protected_strengths': ['drawing silhouette'], 'independent': True,
                       'compared_playback': {'before_ref': 'fixture://before/' + name, 'after_ref': 'fixture://after/' + name, 'source_ref': 'fixture://source'}}}


def audit():
    cases = []
    for name in ('frozen', 'reversed-event', 'copied-photo', 'tiny-no-motion', 'plausible-reference-action', 'missing-playback', 'identity-only', 'unknown-preservation'):
        data = fixture(name)
        if name in ('frozen', 'tiny-no-motion', 'identity-only'):
            data['measured_tests'] = [{'name': 'required_event_motion', 'status': 'fail', 'constraint': True}]
        if name in ('frozen', 'reversed-event'):
            data['source_event_preserved'] = False
        if name == 'copied-photo':
            data['drawing_identity_preserved'] = False
        if name == 'missing-playback':
            data['critic']['scope'] = ['drawing']
            del data['critic']['compared_playback']
        if name == 'unknown-preservation':
            data['source_event_preserved'] = 'unknown'
        decision = evaluate(normalize(data))
        expected = 'accepted' if name == 'plausible-reference-action' else ('milestone_needs_review' if name in ('missing-playback', 'unknown-preservation') else 'rejected')
        require(decision['status'] == expected, 'counterfactual failed: ' + name)
        cases.append({'name': name, 'synthetic_input': data, 'expected_status': expected, 'decision': decision, 'check_passed': True})
    integrity = []
    with tempfile.TemporaryDirectory(prefix='keyframe-ledger-audit-') as directory:
        path = Path(directory) / 'ledger.jsonl'
        init_ledger(path)
        root = fixture('root')
        first = record(root, path)
        child = fixture('child')
        child['parent'] = 'root'
        second = record(child, path)
        sibling = fixture('sibling')
        sibling['parent'] = 'root'
        record(sibling, path)
        require(second['previous_hash'] == first['id'], 'chain linkage')
        require(len(select(path)['candidates']) == 3, 'child history lost')
        integrity.append('hash_chain_and_branch_history')
        for label, candidate in [('duplicate_revision', root), ('missing_parent', dict(fixture('orphan'), parent='absent')), ('duplicate_payload', dict(root, revision='renamed'))]:
            try:
                record(candidate, path)
            except ValueError:
                integrity.append(label + '_refused')
            else:
                raise ValueError(label + ' was not refused')
        unsafe = fixture('unsafe-newest')
        unsafe['drawing_identity_preserved'] = False
        record(unsafe, path)
        require(select(path)['selected_revision'] == 'sibling', 'unsafe candidate selected')
        integrity.append('unsafe_newest_never_selected')
        lines = path.read_text().splitlines()
        altered = json.loads(lines[0])
        altered['input']['revision'] = 'tampered'
        lines[0] = canonical(altered)
        path.write_text('\n'.join(lines) + '\n')
        try:
            select(path)
        except ValueError:
            integrity.append('tampering_detected')
        else:
            raise ValueError('tampering undetected')
    return {'audit_version': 1, 'all_checks_passed': True, 'execution': 'deterministic synthetic gate and integrity tests only',
            'limitations': ['No source/artwork inspection, measured artistic quality, model scores, trained policy, weights, or RL run.', 'Fixture bar_met judgments are assumptions used to test gates, not real critic findings.', 'Hash chain detects edits against retained hashes; it cannot prevent a complete rewrite without an external signed anchor.', 'References and critic independence are declared metadata; this CLI does not authenticate them.'],
            'reward_form': 'preference/constraint vector; no scalar reward', 'counterfactuals': cases, 'integrity_checks': integrity,
            'unexecuted_training_path': ['Collect source-linked state/action/next-state episodes with immutable evidence and independent compared-playback preferences.', 'Imitation warmstart from licensed successful repairs; exclude synthetic audit fixtures.', 'Train an offline preference model with explicit source-event and drawing-identity constraints; evaluate by repair phase.', 'Only after held-out validation, run budgeted online preference collection and constrained policy updates.', 'Hold out both source identities and drawing identities; audit frozen, reversed, photo-copy and tiny-motion failures.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'select', 'record'):
        sub = subs.add_parser(name)
        sub.add_argument('--ledger', required=True, type=Path)
        if name == 'record':
            sub.add_argument('--input', required=True, help='JSON object literal or JSON file path')
    sub = subs.add_parser('audit')
    sub.add_argument('--output', type=Path, help='also save audit JSON')
    args = parser.parse_args()
    try:
        if args.command == 'init':
            result = init_ledger(args.ledger)
        elif args.command == 'record':
            source = args.input
            raw = json.loads(source if source.lstrip().startswith('{') else Path(source).read_text())
            result = record(raw, args.ledger)
        elif args.command == 'select':
            result = select(args.ledger)
        else:
            result = audit()
            if args.output:
                args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
