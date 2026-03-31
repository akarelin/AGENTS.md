#!/usr/bin/env bash
# cleanup-checkins.sh — Rewrite git history to remove Co-Authored-By trailers
# and optionally recreate GitHub releases under the current user.
#
# Usage:
#   cleanup-checkins.sh [--dry-run] [--releases] [<repo-url>]
#
# Options:
#   --dry-run    Clone and rewrite locally but do not push or touch releases
#   --releases   Also delete and recreate GitHub releases (requires gh CLI)
#   <repo-url>   Remote URL (default: origin of current repo)
#
# Prerequisites: git, git-filter-repo (pip install git-filter-repo), gh (optional)

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
DRY_RUN=false
DO_RELEASES=false
REPO_URL=""

# ── Parse args ────────────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --dry-run)    DRY_RUN=true ;;
    --releases)   DO_RELEASES=true ;;
    -*)           echo "Unknown option: $arg" >&2; exit 1 ;;
    *)            REPO_URL="$arg" ;;
  esac
done

# ── Resolve repo URL ─────────────────────────────────────────────────────────
if [[ -z "$REPO_URL" ]]; then
  REPO_URL="$(git remote get-url origin 2>/dev/null || true)"
  if [[ -z "$REPO_URL" ]]; then
    echo "Error: no repo URL provided and no origin remote found." >&2
    exit 1
  fi
fi

REPO_NAME="$(basename "$REPO_URL" .git)"

# ── Preflight checks ─────────────────────────────────────────────────────────
for cmd in git git-filter-repo; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: $cmd not found. Install with: pip install git-filter-repo" >&2
    exit 1
  fi
done

if $DO_RELEASES && ! command -v gh &>/dev/null; then
  echo "Error: --releases requires the GitHub CLI (gh)." >&2
  exit 1
fi

# ── Fresh clone (skip LFS smudge to avoid downloading blobs during rewrite) ──
WORK_DIR="$(mktemp -d)"
echo "» Cloning into $WORK_DIR/$REPO_NAME ..."
GIT_LFS_SKIP_SMUDGE=1 git clone "$REPO_URL" "$WORK_DIR/$REPO_NAME"
cd "$WORK_DIR/$REPO_NAME"

# ── Snapshot releases before rewrite (tags may move) ─────────────────────────
declare -A RELEASES
if $DO_RELEASES && command -v gh &>/dev/null; then
  echo "» Snapshotting GitHub releases ..."
  while IFS=$'\t' read -r tag title; do
    [[ -z "$tag" ]] && continue
    body="$(gh release view "$tag" --json body -q .body 2>/dev/null || true)"
    RELEASES["$tag"]="$title"$'\x1f'"$body"
  done < <(gh release list --limit 100 --json tagName,name -q '.[] | [.tagName, .name] | @tsv')
  echo "  Found ${#RELEASES[@]} release(s)."
fi

# ── Count affected commits ───────────────────────────────────────────────────
AFFECTED=$(git log --all --format="%B" | grep -ci "co-authored-by" || true)
echo "» Found $AFFECTED Co-Authored-By trailer(s) to remove."

if [[ "$AFFECTED" -eq 0 ]]; then
  echo "Nothing to do."
  rm -rf "$WORK_DIR"
  exit 0
fi

# ── Rewrite commit messages ──────────────────────────────────────────────────
echo "» Rewriting history with git-filter-repo ..."
git filter-repo \
  --message-callback '
import re
# Strip Co-Authored-By lines (case-insensitive) and any leading blank lines they leave behind
msg = re.sub(rb"\n+[Cc]o-[Aa]uthored-[Bb]y:.*", b"", message)
# Clean up trailing whitespace
return msg.rstrip() + b"\n"
'

# ── Verify ────────────────────────────────────────────────────────────────────
REMAINING=$(git log --all --format="%B" | grep -ci "co-authored-by" || true)
echo "» Remaining Co-Authored-By trailers: $REMAINING"

if [[ "$REMAINING" -ne 0 ]]; then
  echo "Warning: some trailers were not removed. Inspect manually." >&2
fi

# ── Push ──────────────────────────────────────────────────────────────────────
if $DRY_RUN; then
  echo "» Dry run — skipping push. Rewritten repo at: $WORK_DIR/$REPO_NAME"
  exit 0
fi

echo "» Pushing rewritten history ..."
git remote add origin "$REPO_URL"
git push --force --all
git push --force --tags

# ── Recreate GitHub releases ─────────────────────────────────────────────────
if $DO_RELEASES && [[ ${#RELEASES[@]} -gt 0 ]]; then
  echo "» Recreating ${#RELEASES[@]} GitHub release(s) ..."
  for tag in "${!RELEASES[@]}"; do
    IFS=$'\x1f' read -r title body <<< "${RELEASES[$tag]}"
    echo "  Deleting release $tag ..."
    gh release delete "$tag" --yes 2>/dev/null || true
    echo "  Creating release $tag ..."
    gh release create "$tag" --title "$title" --notes "$body"
  done
  echo "» Releases recreated under current gh user."
fi

# ── Cleanup ───────────────────────────────────────────────────────────────────
echo "» Cleaning up temp directory ..."
rm -rf "$WORK_DIR"
echo "Done."
