#!/usr/bin/env python3
"""Dry-run history rewrite across a list of repos. Writes a markdown report.

Usage:
    WORK=/path OWNER=akarelin REPOS="a,b,c" dryrun.py /path/to/report.md

Expects $WORK/mailmap and $WORK/callback.py to exist. Clones each repo fresh
into $WORK/<name>.git, runs filter-repo locally (no push), and generates
per-repo stats: branch/tag counts, pre-rewrite commit count, trailer matches,
release-note matches.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import date

WORK = Path(os.environ.get('WORK', '/tmp/rewrite-dryrun'))
OWNER = os.environ.get('OWNER', 'akarelin')
REPOS = [r.strip() for r in os.environ.get('REPOS', '').split(',') if r.strip()]
REPORT = Path(sys.argv[1]) if len(sys.argv) > 1 else WORK / 'rewrite-plan.md'

if not REPOS:
    sys.exit('set REPOS=a,b,c')
MAILMAP = WORK / 'mailmap'
CB_FILE = WORK / 'callback.py'
if not MAILMAP.exists() or not CB_FILE.exists():
    sys.exit(f'missing {MAILMAP} or {CB_FILE}')
CALLBACK = CB_FILE.read_text()

TRAILER_RE = re.compile(
    r'(Co-authored-by|Generated (with|by)).*(Claude|Codex|Bots|Manus|Copilot|Dependabot|github-actions)',
    re.I,
)
SSH_ENV = {**os.environ, 'GIT_SSH_COMMAND': 'ssh -o IdentitiesOnly=yes'}


def run(cmd, cwd=None, env=None, check=False):
    return subprocess.run(cmd, cwd=cwd, env=env or os.environ, capture_output=True, check=check)


def clone(repo, dest):
    if dest.exists():
        shutil.rmtree(dest)
    r = run(['git', 'clone', '--mirror', f'git@github.com:{OWNER}/{repo}.git', str(dest)], env=SSH_ENV)
    return r.returncode == 0, r.stderr.decode('utf-8', 'replace')


def author_counts(git_dir, ref_filter='--branches'):
    r = run(['git', '--git-dir', str(git_dir), 'log', ref_filter, '--format=%an <%ae>'])
    if r.returncode != 0:
        return []
    counts = {}
    for line in r.stdout.decode('utf-8', 'replace').splitlines():
        counts[line] = counts.get(line, 0) + 1
    return sorted(counts.items(), key=lambda x: -x[1])


def trailer_commit_count(git_dir):
    r = run(['git', '--git-dir', str(git_dir), 'log', '--branches', '--format=%H%x00%B%x00%x00'])
    if r.returncode != 0:
        return 0
    blob = r.stdout.decode('utf-8', 'replace')
    return sum(1 for c in blob.split('\x00\x00')
               if (p := c.split('\x00', 1)) and len(p) == 2 and TRAILER_RE.search(p[1]))


def count_refs(git_dir, prefix):
    r = run(['git', '--git-dir', str(git_dir), 'for-each-ref', prefix])
    return len(r.stdout.decode().splitlines())


def scan_releases(repo):
    r = run(['gh', 'release', 'list', '--repo', f'{OWNER}/{repo}', '--limit', '500', '--json', 'tagName'])
    if r.returncode != 0:
        return 0, []
    try:
        releases = json.loads(r.stdout.decode('utf-8', 'replace') or '[]')
    except json.JSONDecodeError:
        return 0, []
    hits = []
    for rel in releases:
        tag = rel.get('tagName', '')
        if not tag:
            continue
        rr = run(['gh', 'release', 'view', tag, '--repo', f'{OWNER}/{repo}', '--json', 'body'])
        if rr.returncode != 0:
            continue
        try:
            body = json.loads(rr.stdout.decode('utf-8', 'replace')).get('body') or ''
        except json.JSONDecodeError:
            continue
        if TRAILER_RE.search(body):
            hits.append(tag)
    return len(releases), hits


def run_filter(git_dir, purge_globs):
    args = ['git', 'filter-repo', '--force', '--mailmap', str(MAILMAP), '--commit-callback', CALLBACK]
    for g in purge_globs or []:
        args += ['--path-glob', g, '--invert-paths']
    return run(args, cwd=git_dir)


def render_authors(entries, limit=15):
    if not entries:
        return '  (none)'
    return '\n'.join(f'  {n:>6}  {ident}' for ident, n in entries[:limit])


def main():
    lines = [
        f'# Rewrite Plan — {date.today()}',
        '',
        f'**Scope:** {len(REPOS)} repos under `{OWNER}/`.',
        '',
        '## Mailmap', '```', MAILMAP.read_text().strip(), '```', '',
        '## Per-repo plan', '',
    ]
    for repo in REPOS:
        print(f'scanning {repo}...', file=sys.stderr, flush=True)
        dest = WORK / f'{repo}.git'
        ok, err = clone(repo, dest)
        if not ok:
            lines += [f'### {repo}', '', '- **CLONE FAILED**', '```', err.strip()[:800], '```', '']
            continue
        branches = count_refs(dest, 'refs/heads/')
        tags = count_refs(dest, 'refs/tags/')
        pre_authors = author_counts(dest)
        pre_count = sum(n for _, n in pre_authors)
        pre_trailers = trailer_commit_count(dest)
        if branches == 0:
            lines += [f'### {repo}', '', f'- Empty. Tags: {tags}. Skipped.', '']
            continue
        purge_env = os.environ.get(f'PURGE_{repo}', '')
        purge = [purge_env] if purge_env else []
        fr = run_filter(dest, purge)
        fr_ok = fr.returncode == 0
        post_authors = author_counts(dest) if fr_ok else []
        post_count = sum(n for _, n in post_authors)
        rel_total, rel_hits = scan_releases(repo)

        section = [
            f'### {repo}', '',
            f'- Branches: {branches}, Tags: {tags}',
            f'- Commits on branches: before {pre_count} → after {post_count}',
            f'- Co-author trailers to strip: {pre_trailers} commit(s)',
            f'- Releases: {rel_total} total',
        ]
        section.append(
            f'- Release notes to edit ({len(rel_hits)}): `{", ".join(rel_hits)}`'
            if rel_hits else '- Release notes to edit: none'
        )
        if not fr_ok:
            section += ['', '**filter-repo ERROR:**', '```', fr.stderr.decode('utf-8', 'replace')[-400:], '```']
        section += [
            '', '**Authors (before):**', '```', render_authors(pre_authors), '```',
            '', '**Authors (after):**', '```', render_authors(post_authors, 5), '```', '',
        ]
        lines += section

    lines += ['---', f'Generated {date.today().isoformat()}']
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text('\n'.join(lines) + '\n')
    print(f'wrote {REPORT}', file=sys.stderr)


if __name__ == '__main__':
    main()
