#!/bin/bash
# Spawn the three Phase-3 parallel track sessions in detached tmux windows.
# Idempotent: kills any existing track{1,2,3} tmux sessions first.

set -e
REPO="/Users/alex/A/SessionManager"
PROMPTS="$REPO/docs/tracks/spawn"

for s in track1 track2 track3; do
    tmux kill-session -t "$s" 2>/dev/null || true
done

spawn() {
    local name="$1"
    local prompt_file="$2"
    local prompt
    prompt=$(cat "$prompt_file")
    tmux new-session -d -s "$name" -c "$REPO" \
        "claude $(printf '%q' "$prompt")"
    echo "spawned $name ← $prompt_file"
}

spawn track1 "$PROMPTS/track-1.prompt.txt"
spawn track2 "$PROMPTS/track-2.prompt.txt"
spawn track3 "$PROMPTS/track-3.prompt.txt"

echo
echo "Active sessions:"
tmux ls
echo
echo "Attach with:  tmux attach -t track1   (or track2 / track3)"
echo "Detach with:  Ctrl-b d"
echo "Kill all:     for s in track1 track2 track3; do tmux kill-session -t \$s; done"
