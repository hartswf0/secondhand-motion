"""Check every lot before the site is built. Exit 1 on any problem.

usage: python3 tools/validate.py
Checks: required fields, unique lot numbers, known kind/lane/status, files that items point to exist,
test ids exist in tests/registry.json.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from new_subject import lot_files

KINDS = {'shot', 'subject', 'batch', 'study', 'dataset', 'doc'}
LANES = {'data', 'look', 'motion', 'join', 'queue', 'method'}
STATUS = {'queued', 'in progress', 'done', 'failed', 'parked'}
REQ = ['lot', 'id', 'kind', 'title', 'lane', 'status', 'added', 'blurb', 'links']


def check(prebuild=False):
    """prebuild=True skips links into pages/, which the build itself writes."""
    reg = {t['id'] for t in json.load(open(ROOT / 'tests/registry.json'))['tests']}
    errs, seen = [], {}
    for p in lot_files():
        rel = p.relative_to(ROOT); it = json.load(open(p))
        for k in REQ:
            if k not in it: errs.append(f'{rel}: missing {k}')
        if it.get('lot') in seen: errs.append(f'{rel}: lot {it["lot"]} also used by {seen[it["lot"]]}')
        seen[it.get('lot')] = rel
        if it.get('kind') not in KINDS: errs.append(f'{rel}: kind {it.get("kind")!r}')
        if it.get('lane') not in LANES: errs.append(f'{rel}: lane {it.get("lane")!r}')
        if it.get('status') not in STATUS: errs.append(f'{rel}: status {it.get("status")!r}')
        for f in ['cover', 'cover_alt', 'tests']:
            if it.get(f) and not (ROOT / it[f]).exists(): errs.append(f'{rel}: {f} {it[f]} not found')
        for l in it.get('links', []):
            h = l.get('href') or ''
            if h and not h.startswith('http') and not (prebuild and h.startswith('pages/')) and not (ROOT / h.split('#')[0]).exists(): errs.append(f'{rel}: link {h} not found')
        if it.get('tests'):
            for t in json.load(open(ROOT / it['tests'])):
                if t['id'] not in reg: errs.append(f'{rel}: test {t["id"]} not in registry')
    return errs, len(seen)


if __name__ == '__main__':
    errs, n = check()
    for e in errs: print('ERROR', e)
    print(f'{n} lots, {len(errs)} problems'); sys.exit(1 if errs else 0)
