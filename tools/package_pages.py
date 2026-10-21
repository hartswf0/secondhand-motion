"""Audit a lean Pages payload and generate explicit legacy-Jekyll exclusions.

The repository and repair history are never removed or rewritten. Only unlinked
diagnostic copies are candidates for exclusion from the public web payload.
Current HTML, JSON, data, native drawn keys and media remain unchanged. Existing
local references in retained HTML/JSON/CSS/JS/Markdown protect candidate files.
Do not place .nojekyll at the publishing root when using generated _config.yml.
Rerun after final page/data generation before publishing: a new public link into
a formerly excluded directory must refresh these explicit exclusions.

  python tools/package_pages.py --report /tmp/pages-report.json --write-config
  python tools/package_pages.py --output /tmp/lean-site --report /tmp/pages-report.json

The optional output is a byte-identical static payload for inspection. It is not
a replacement repository or an automatic claim that Jekyll was executed locally.
"""
from pathlib import Path
from collections import deque
from html.parser import HTMLParser
import argparse
import fnmatch
import html
import json
import re
import shutil
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {'.html', '.htm', '.json', '.css', '.js', '.mjs', '.md', '.txt'}
WEB_SUFFIXES = r'(?:html?|json|jsonl|css|m?js|png|jpe?g|gif|webp|svg|ico|mp4|webm|mov|mp3|wav|ogg|pdf|csv|txt|md|py|ndjson|zip)'
QUOTED = re.compile(r'''["']([^"'<>\n\r]{1,1200}?\.'''+WEB_SUFFIXES+r'''(?:[?#][^"'<>\n\r]*)?)["']''', re.I)
MARKDOWN = re.compile(r'\]\(([^)\s]+)(?:\s+[^)]*)?\)')


def inventory(root):
    output = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root)
    names = set(output.decode().split('\0'))
    return {name: root/name for name in names if name and (root/name).is_file()
            and not any(p.startswith('.') for p in Path(name).parts)
            and not name.startswith('_site/')}


def diagnostic(name):
    p = Path(name)
    parts = p.parts
    if not parts or parts[0] != 'shots':
        return False  # In particular batches/**/revisions contain selected art.
    if len(parts) > 3 and parts[2:4] == ('integrated', 'revisions'):
        return True
    if len(parts) > 3 and parts[2] == 'drawn' and p.suffix.lower() in {'.png', '.jpg', '.jpeg'}:
        return p.name.startswith('check-') or p.name.startswith('frames-')
    if len(parts) > 3 and parts[2] in {'sheets', 'survey', 'critic'}:
        return p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}
    return False


class Attributes(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        self.references += [v for k, v in attrs if k in {'href', 'src', 'poster', 'data-src'} and v]
        for k, v in attrs:
            if k == 'srcset' and v:
                self.references += [entry.strip().split()[0] for entry in v.split(',') if entry.strip()]


def references(text, suffix):
    text = text.replace('\\/', '/')
    refs = [m.group(1) for m in QUOTED.finditer(text)]
    refs += [m.group(1) for m in MARKDOWN.finditer(text)]
    if suffix in {'.html', '.htm'}:
        parser = Attributes()
        parser.feed(text)
        refs += parser.references
    return set(refs)


def resolve(ref, origin, files):
    ref = html.unescape(ref).strip()
    if not ref or ref.startswith(('#', 'data:', 'mailto:', 'javascript:', '//')):
        return []
    split = urlsplit(ref)
    if split.scheme or split.netloc:
        return []
    value = unquote(split.path)
    if not value or any(token in value for token in ['<', '>', '${', '{slug}', '*']):
        return []
    candidates = []
    # Explicit repo-root paths in JSON and relative URL paths in pages both occur.
    if value.startswith('/secondhand-motion/'):
        value = value[len('/secondhand-motion/'):]
        candidates.append(value)
    elif value.startswith('/'):
        candidates.append(value.lstrip('/'))
    else:
        candidates += [str(Path(origin).parent/value), value]
    found = []
    for item in candidates:
        parts = []
        for part in Path(item).parts:
            if part == '..':
                if not parts:
                    parts = []
                    break
                parts.pop()
            elif part not in {'.', ''}:
                parts.append(part)
        normalized = '/'.join(parts)
        if normalized in files:
            found.append(normalized)
        elif normalized.rstrip('/')+'/index.html' in files:
            found.append(normalized.rstrip('/')+'/index.html')
    return sorted(set(found))


def audit(root=ROOT):
    root = Path(root).resolve()
    files = inventory(root)
    candidates = {name for name in files if diagnostic(name)}
    included = set(files)-candidates
    pending = deque(name for name in included if Path(name).suffix.lower() in TEXT_SUFFIXES)
    scanned = set()
    protected = {}
    checked_references = 0
    while pending:
        origin = pending.popleft()
        if origin in scanned:
            continue
        scanned.add(origin)
        try:
            text = files[origin].read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for ref in references(text, Path(origin).suffix.lower()):
            targets = resolve(ref, origin, files)
            checked_references += len(targets)
            for target in targets:
                if target in candidates:
                    protected.setdefault(target, []).append(dict(origin=origin, reference=ref))
                if target not in included:
                    included.add(target)
                    if Path(target).suffix.lower() in TEXT_SUFFIXES:
                        pending.append(target)
    excluded = sorted(set(files)-included)
    # A second closure pass establishes no resolved literal reference crosses into
    # the excluded payload. Dynamic paths are separately reported, never guessed.
    crossing = []
    dynamic = []
    for origin in sorted(scanned):
        text = files[origin].read_text(errors='replace')
        for ref in references(text, Path(origin).suffix.lower()):
            for target in resolve(ref, origin, files):
                if target not in included:
                    crossing.append(dict(origin=origin, reference=ref, target=target))
        for line in text.splitlines():
            if ('${' in line or '+slug+' in line or '+selected+' in line) and any(t in line for t in ['revisions/', '/drawn/', 'sheets/', 'survey/', 'critic/']):
                dynamic.append(origin)
    assert not crossing, 'Resolved public reference would be excluded'
    # Protect all diagnostic candidates under dynamic diagnostic directory roots.
    # Current player templates create final paths, not these diagnostic paths.
    # Any new dynamic diagnostic path must receive an explicit audit first.
    assert not dynamic, 'Dynamic diagnostic paths require explicit protection: '+', '.join(sorted(set(dynamic)))
    total = sum(path.stat().st_size for path in files.values())
    payload = sum(files[name].stat().st_size for name in included)
    return dict(scope='Only unlinked diagnostic copies excluded; repository bytes/history unchanged. Literal local reference closure checked across retained web text; dynamic diagnostic paths fail closed.',
                total_files=len(files), included_files=len(included), excluded_files=len(excluded),
                total_bytes=total, payload_bytes=payload, saved_bytes=total-payload,
                payload_mib=round(payload/2**20, 3), saved_mib=round((total-payload)/2**20, 3),
                scanned_text_files=len(scanned), checked_existing_references=checked_references,
                unresolved_existing_crossings=crossing, dynamic_diagnostic_pages=sorted(set(dynamic)),
                protected_diagnostics=protected, exclusions=excluded,
                provenance='Full revisions, source inputs and diagnostic images remain available in the GitHub repository.'), included, files


def config_text(report):
    # Exact file/directory paths avoid glob-version differences. A directory can
    # only replace individual files when every inventoried child was excluded.
    rows = ['# Generated by python tools/package_pages.py --write-config',
            '# Legacy branch build: remove .nojekyll so these exclusions apply.',
            '# Full source/history remains in git; only unlinked web diagnostics omitted.',
            'theme: null', 'plugins: []', 'exclude:']
    rows += ['  - '+json.dumps(name) for name in report['config_exclusions']]
    rows += ['', '# Leave prebuilt HTML without front matter as static files.',
             'defaults: []', 'titles_from_headings:', '  enabled: false',
             'readme_index:', '  enabled: false', 'optional_front_matter:', '  enabled: false', '']
    return '\n'.join(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--write-config', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--max-mib', type=float, default=900.0)
    args = parser.parse_args()
    report, included, files = audit(args.root)
    counts, omitted = {}, {}
    for name in files:
        for parent in Path(name).parents:
            key = parent.as_posix()
            if key == '.':
                continue
            counts[key] = counts.get(key, 0)+1
    for name in report['exclusions']:
        for parent in Path(name).parents:
            key = parent.as_posix()
            if key == '.':
                continue
            omitted[key] = omitted.get(key, 0)+1
    covered, compact = set(), []
    for directory in sorted((k for k, n in omitted.items() if counts[k] == n), key=lambda p: (len(Path(p).parts), p)):
        if not any(directory == c or directory.startswith(c+'/') for c in covered):
            compact.append(directory)
            covered.add(directory)
    compact += [name for name in report['exclusions'] if not any(name.startswith(c+'/') for c in covered)]
    report['config_exclusions'] = sorted(compact)
    report['retained_html_front_matter'] = [name for name in sorted(included)
                                           if Path(name).suffix.lower() in {'.html', '.htm'}
                                           and files[name].read_bytes().startswith((b'---\n', b'---\r\n', b'\xef\xbb\xbf---'))]
    assert not report['retained_html_front_matter'], 'Prebuilt HTML must remain static; front matter needs a separate rendering audit'
    assert report['payload_mib'] < args.max_mib, f'Payload {report["payload_mib"]} MiB exceeds {args.max_mib} MiB budget'
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
    if args.write_config:
        (args.root/'_config.yml').write_text(config_text(report))
    if args.output:
        assert not args.output.exists(), 'Output must be new; existing directories are never removed'
        args.output.mkdir(parents=True)
        for name in sorted(included):
            target = args.output/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(files[name], target)
    print(json.dumps({k: report[k] for k in ['total_files', 'included_files', 'excluded_files', 'payload_mib', 'saved_mib', 'scanned_text_files', 'checked_existing_references', 'unresolved_existing_crossings', 'dynamic_diagnostic_pages']}))


if __name__ == '__main__':
    main()
