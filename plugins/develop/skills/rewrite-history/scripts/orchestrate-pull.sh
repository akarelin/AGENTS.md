#!/usr/bin/env bash
# Fan out pull-host.sh / pull-host.ps1 after a force-push rewrite to reconcile all workstation clones.
#
# Usage: WORK=/path HOSTS="kolme seven ..." REPOS="a,b,c" [OWNER=akarelin] orchestrate-pull.sh
set -u
: "${WORK:?set WORK}"
: "${HOSTS:?set HOSTS space-separated SSH aliases}"
: "${REPOS:?set REPOS comma-separated repo names}"
OWNER="${OWNER:-akarelin}"

LOGS=$WORK/pull-logs
mkdir -p "$LOGS"; rm -f "$LOGS"/*.log
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_ssh() {
  local h="$1" log="$LOGS/${h//\//_}.log"
  {
    echo "=== ssh $h ==="
    scp -q -o ConnectTimeout=5 -o BatchMode=yes "$SELF_DIR/pull-host.sh" "$h:/tmp/pull-host.sh" 2>&1
    ssh -o ConnectTimeout=5 -o BatchMode=yes "$h" \
      "chmod +x /tmp/pull-host.sh && OWNER='$OWNER' /tmp/pull-host.sh '$REPOS'; rm -f /tmp/pull-host.sh" 2>&1
    echo "=== done $h ==="
  } > "$log" 2>&1
  echo "ssh-$h done"
}

run_local_wsl() {
  local log="$LOGS/alex-pc-wsl.log"
  { OWNER="$OWNER" bash "$SELF_DIR/pull-host.sh" "$REPOS" 2>&1; } > "$log" 2>&1
  echo "local-wsl done"
}

run_local_windows() {
  local log="$LOGS/alex-pc-windows.log"
  { powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(wslpath -w "$SELF_DIR/pull-host.ps1")" -Repos "$REPOS" -Owner "$OWNER" 2>&1; } > "$log" 2>&1
  echo "local-ps done"
}

echo "Pull-phase: fanning out..."
for h in $HOSTS; do run_ssh "$h" & done
run_local_wsl &
command -v powershell.exe >/dev/null 2>&1 && run_local_windows &
wait

echo
echo "=== Summary ==="
for f in "$LOGS"/*.log; do
  echo
  echo "--- $(basename "$f" .log) ---"
  grep -E "OK|FAIL|SKIP|SAME|WARN|done\." "$f" | head -60
done
