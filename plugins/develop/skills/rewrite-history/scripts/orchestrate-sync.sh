#!/usr/bin/env bash
# Fan out sync-host.sh to SSH-reachable Linux/Mac hosts + alex-pc WSL + alex-pc Windows (DevDrive via powershell.exe).
# Logs per-host in $WORK/sync-logs/*.log.
#
# Usage: WORK=/path HOSTS="kolme seven ..." REPOS="a,b,c" [OWNER=akarelin] orchestrate-sync.sh
set -u
: "${WORK:?set WORK}"
: "${HOSTS:?set HOSTS space-separated SSH aliases}"
: "${REPOS:?set REPOS comma-separated repo names}"
OWNER="${OWNER:-akarelin}"

LOGS=$WORK/sync-logs
mkdir -p "$LOGS"; rm -f "$LOGS"/*.log
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_ssh() {
  local h="$1" log="$LOGS/${h//\//_}.log"
  {
    echo "=== ssh $h ==="
    scp -q -o ConnectTimeout=5 -o BatchMode=yes "$SELF_DIR/sync-host.sh" "$h:/tmp/sync-host.sh" 2>&1
    ssh -o ConnectTimeout=5 -o BatchMode=yes "$h" \
      "chmod +x /tmp/sync-host.sh && OWNER='$OWNER' /tmp/sync-host.sh '$REPOS'; rm -f /tmp/sync-host.sh" 2>&1
    echo "=== done $h ==="
  } > "$log" 2>&1
  echo "ssh-$h done"
}

run_local_wsl() {
  local log="$LOGS/alex-pc-wsl.log"
  { OWNER="$OWNER" bash "$SELF_DIR/sync-host.sh" "$REPOS" 2>&1; } > "$log" 2>&1
  echo "local-wsl done"
}

run_local_windows() {
  local log="$LOGS/alex-pc-windows.log"
  { powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(wslpath -w "$SELF_DIR/sync-host.ps1")" -Repos "$REPOS" -Owner "$OWNER" 2>&1; } > "$log" 2>&1
  echo "local-ps done"
}

echo "Sync-phase: fanning out..."
for h in $HOSTS; do run_ssh "$h" & done
run_local_wsl &
command -v powershell.exe >/dev/null 2>&1 && run_local_windows &
wait

echo
echo "=== Summary ==="
for f in "$LOGS"/*.log; do
  echo
  echo "--- $(basename "$f" .log) ---"
  grep -E "OK|FAIL|COMMIT|PUSH|DIRTY|SKIP|done\." "$f" | head -60
done
