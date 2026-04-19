#!/usr/bin/env bash
# Pre-rewrite per-host sync. Runs on Linux/Mac/WSL.
# Usage: sync-host.sh <owner>/<repo>,<owner>/<repo>,... OR just repo,repo,... with OWNER= env.
# For each matching clone: auto-commit dirty → fetch → pull --rebase → push → log.
set -u
SPEC="${1:-}"
[[ -z "$SPEC" ]] && { echo "usage: $0 repo1,repo2,..."; exit 2; }
IFS=',' read -ra REPO_ARR <<< "$SPEC"
OWNER="${OWNER:-akarelin}"

HOST="$(hostname)"
STAMP="$(date +%Y-%m-%d)"
ROOTS=("$HOME" "$HOME/CRAP" "$HOME/dev" "$HOME/code" "$HOME/src")

log() { printf '[%s] %s\n' "$HOST" "$*"; }

sync_clone() {
  local wd="$1" repo="$2"
  local branch; branch=$(git -C "$wd" symbolic-ref --short HEAD 2>/dev/null || echo '')
  [[ -z "$branch" ]] && { log "SKIP  $repo  $wd  (detached HEAD)"; return; }
  local dirty; dirty=$(git -C "$wd" status --porcelain 2>/dev/null)
  if [[ -n "$dirty" ]]; then
    log "DIRTY $repo  $wd  ($(echo "$dirty" | wc -l) files)"
    git -C "$wd" add -A 2>&1 || { log "FAIL  $repo  $wd  add"; return; }
    git -C "$wd" -c user.name="$(git -C "$wd" config user.name || echo 'Auto')" \
                 -c user.email="$(git -C "$wd" config user.email || echo 'auto@local')" \
                 commit -m "auto: pre-rewrite snapshot ${STAMP}" 2>&1 | tail -2 \
      || { log "FAIL  $repo  $wd  commit"; return; }
    log "COMMIT $repo  $wd"
  fi
  git -C "$wd" -c fetch.recurseSubmodules=no fetch origin 2>&1 | tail -2 \
    || { log "FAIL  $repo  $wd  fetch"; return; }
  local upstream; upstream=$(git -C "$wd" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || echo '')
  [[ -z "$upstream" ]] && { log "SKIP  $repo  $wd  no upstream on $branch"; return; }
  if ! git -C "$wd" pull --rebase 2>&1 | tail -5; then
    log "FAIL  $repo  $wd  pull --rebase"; return
  fi
  local ahead; ahead=$(git -C "$wd" rev-list --count "${upstream}..HEAD" 2>/dev/null || echo 0)
  if [[ "$ahead" -gt 0 ]]; then
    git -C "$wd" push 2>&1 | tail -3 || { log "FAIL  $repo  $wd  push"; return; }
    log "PUSH  $repo  $wd  $ahead commits -> $upstream"
  fi
  log "OK    $repo  $wd  clean on $branch"
}

for R in "${ROOTS[@]}"; do
  [[ -d "$R" ]] || continue
  while IFS= read -r gitdir; do
    wd="$(dirname "$gitdir")"
    url=$(git -C "$wd" config --get remote.origin.url 2>/dev/null || echo '')
    [[ -z "$url" ]] && continue
    for repo in "${REPO_ARR[@]}"; do
      if [[ "$url" == *"${OWNER}/${repo}.git"* || "$url" == *"${OWNER}/${repo}" ]]; then
        sync_clone "$wd" "$repo"; break
      fi
    done
  done < <(find "$R" -maxdepth 4 -type d -name ".git" 2>/dev/null)
done
log "done."
