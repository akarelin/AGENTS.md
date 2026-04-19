#!/usr/bin/env bash
# Full pipeline per repo: pull → mailmap+callback rewrite → force-push heads+tags+LFS → edit release notes.
# Runs configured repos in parallel, one log per repo.
#
# Usage:
#   WORK=/path/to/work OWNER=akarelin REPOS="repo1,repo2,..." pipeline.sh
#
# Expects $WORK/mailmap and $WORK/callback.py to exist.
# Per-CRAP-style purges: set PURGE_<repo>='*.arw' env var (repeat as needed).
set -u
: "${WORK:?set WORK to a writable dir on a real filesystem (not tmpfs)}"
: "${OWNER:?set OWNER, e.g. OWNER=akarelin}"
: "${REPOS:?set REPOS, e.g. REPOS=foo,bar,baz}"

MAILMAP=$WORK/mailmap
CB_FILE=$WORK/callback.py
[[ -f "$MAILMAP" ]] || { echo "missing $MAILMAP"; exit 2; }
[[ -f "$CB_FILE" ]] || { echo "missing $CB_FILE"; exit 2; }
CB=$(cat "$CB_FILE")

LOGS=$WORK/push-logs
mkdir -p "$LOGS"
SSH_ENV='ssh -o IdentitiesOnly=yes'
STAMP=$(date +%Y-%m-%dT%H%M%S)

IFS=',' read -ra REPO_ARR <<< "$REPOS"

process_repo() {
  local r="$1"
  local D=$WORK/$r.git
  local log=$LOGS/${r}.log
  local url="git@github.com:${OWNER}/${r}.git"
  local purge_var="PURGE_${r}"
  local purge="${!purge_var:-}"
  {
    echo "=== $r @ $STAMP ==="
    echo "-- clone --"
    rm -rf "$D"
    GIT_SSH_COMMAND="$SSH_ENV" git clone --mirror "$url" "$D" 2>&1 | tail -3
    [[ ! -d "$D" ]] && { echo "FAIL: clone"; return; }
    echo "-- lfs fetch --"
    GIT_SSH_COMMAND="$SSH_ENV" git -C "$D" lfs fetch --all origin 2>&1 | tail -2 || true
    echo "-- filter-repo --"
    local FR_ARGS=(--force --mailmap "$MAILMAP" --commit-callback "$CB")
    [[ -n "$purge" ]] && FR_ARGS+=(--path-glob "$purge" --invert-paths)
    (cd "$D" && git filter-repo "${FR_ARGS[@]}" 2>&1 | tail -3)
    echo "-- restore origin --"
    git -C "$D" remote remove origin 2>&1 | tail -1 || true
    git -C "$D" remote add origin "$url"
    echo "-- lfs push --"
    GIT_SSH_COMMAND="$SSH_ENV" git -C "$D" lfs push --all origin 2>&1 | tail -2 || true
    echo "-- push heads --"
    local branches
    mapfile -t branches < <(git -C "$D" for-each-ref --format='%(refname)' refs/heads/)
    for b in "${branches[@]}"; do
      GIT_SSH_COMMAND="$SSH_ENV" git -C "$D" push --force origin "${b}:${b}" 2>&1 | tail -3 || echo "FAIL push $b"
    done
    echo "-- push tags (batched) --"
    GIT_SSH_COMMAND="$SSH_ENV" git -C "$D" push --force origin 'refs/tags/*:refs/tags/*' 2>&1 | tail -5 || echo "FAIL tag batch"
    echo "-- release notes scan --"
    python3 - "$OWNER" "$r" <<'PY'
import json, subprocess, sys, re
owner, repo = sys.argv[1], sys.argv[2]
rgx = re.compile(r'(Co-authored-by|Generated (with|by)).*(Claude|Codex|Bots|Manus|Copilot|Dependabot|github-actions)', re.I)
try:
    p = subprocess.run(['gh', 'release', 'list', '--repo', f'{owner}/{repo}', '--limit', '500', '--json', 'tagName'],
                       capture_output=True, text=True, check=True)
    releases = json.loads(p.stdout or '[]')
except Exception as e:
    print(f'  release list failed: {e}')
    releases = []
edited = 0
for rel in releases:
    tag = rel.get('tagName', '')
    if not tag: continue
    try:
        v = subprocess.run(['gh', 'release', 'view', tag, '--repo', f'{owner}/{repo}', '--json', 'body'],
                           capture_output=True, text=True, check=True)
        body = json.loads(v.stdout).get('body') or ''
    except Exception:
        continue
    if not rgx.search(body): continue
    new = body
    new = re.sub(r'(?im)^.*Co-authored-by:\s*.*(Claude|Codex|Bots|Manus|Copilot|Dependabot|github-actions).*(?:\r?\n)?', '', new)
    new = re.sub(r'(?im)^.*Generated (?:with|by).*(Claude|Codex|Bots|Manus|Copilot).*(?:\r?\n)?', '', new)
    new = re.sub(r'(\r?\n){3,}', '\n\n', new).rstrip() + '\n'
    if new.strip() == body.strip(): continue
    try:
        subprocess.run(['gh', 'release', 'edit', tag, '--repo', f'{owner}/{repo}', '--notes', new],
                       capture_output=True, text=True, check=True)
        print(f'  edited release {tag}')
        edited += 1
    except subprocess.CalledProcessError as e:
        print(f'  FAIL edit {tag}: {e.stderr[:200]}')
print(f'  releases scanned: {len(releases)}, edited: {edited}')
PY
    echo "=== done $r ==="
  } > "$log" 2>&1
  echo "done: $r"
}

echo "Pipeline start: ${#REPO_ARR[@]} repos in parallel"
for r in "${REPO_ARR[@]}"; do
  process_repo "$r" &
done
wait
echo "Pipeline complete"
