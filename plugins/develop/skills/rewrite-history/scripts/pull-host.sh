#!/usr/bin/env bash
# Post-force-push per-host pull. Runs on Linux/Mac/WSL.
# Usage: pull-host.sh <comma-separated-repo-names>    OWNER= env overrides owner (default: akarelin)
# For each matching clone: fetch origin (no submodules) → reset --hard origin/<branch>.
set -u
SPEC="${1:-}"
[[ -z "$SPEC" ]] && { echo "usage: $0 repo1,repo2,..."; exit 2; }
IFS=',' read -ra REPO_ARR <<< "$SPEC"
OWNER="${OWNER:-akarelin}"

HOST="$(hostname)"
ROOTS=("$HOME" "$HOME/CRAP" "$HOME/dev" "$HOME/code" "$HOME/src")
log() { printf '[%s] %s\n' "$HOST" "$*"; }

pull_clone() {
  local wd="$1" repo="$2"
  local branch; branch=$(git -C "$wd" symbolic-ref --short HEAD 2>/dev/null || echo '')
  [[ -z "$branch" ]] && { log "SKIP  $repo  $wd  (detached HEAD)"; return; }
  local dirty; dirty=$(git -C "$wd" status --porcelain 2>/dev/null)
  if [[ -n "$dirty" ]]; then
    log "SKIP  $repo  $wd  DIRTY ($(echo "$dirty" | wc -l) files)"
    return
  fi
  local fout; fout=$(git -C "$wd" -c fetch.recurseSubmodules=no fetch origin --prune --prune-tags --tags --force 2>&1)
  if [[ $? -ne 0 ]]; then
    log "FAIL  $repo  $wd  fetch: $(echo "$fout" | tail -2)"; return
  fi
  local upstream; upstream=$(git -C "$wd" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || echo '')
  [[ -z "$upstream" ]] && { log "SKIP  $repo  $wd  no upstream on $branch"; return; }
  local before after
  before=$(git -C "$wd" rev-parse HEAD 2>/dev/null)
  git -C "$wd" reset --hard "$upstream" >/dev/null 2>&1 || { log "FAIL  $repo  $wd  reset"; return; }
  after=$(git -C "$wd" rev-parse HEAD 2>/dev/null)
  if git -C "$wd" lfs env >/dev/null 2>&1 && grep -q "lfs" "$wd/.gitattributes" 2>/dev/null; then
    git -C "$wd" lfs pull >/dev/null 2>&1 || log "WARN  $repo  $wd  lfs pull failed"
  fi
  if [[ "$before" == "$after" ]]; then
    log "SAME  $repo  $wd  at $upstream (${after:0:8})"
  else
    log "OK    $repo  $wd  ${before:0:8} -> ${after:0:8} on $branch"
  fi
}

for R in "${ROOTS[@]}"; do
  [[ -d "$R" ]] || continue
  while IFS= read -r gitdir; do
    wd="$(dirname "$gitdir")"
    url=$(git -C "$wd" config --get remote.origin.url 2>/dev/null || echo '')
    [[ -z "$url" ]] && continue
    for repo in "${REPO_ARR[@]}"; do
      if [[ "$url" == *"${OWNER}/${repo}.git"* || "$url" == *"${OWNER}/${repo}" ]]; then
        pull_clone "$wd" "$repo"; break
      fi
    done
  done < <(find "$R" -maxdepth 4 -type d -name ".git" 2>/dev/null)
done
log "done."
