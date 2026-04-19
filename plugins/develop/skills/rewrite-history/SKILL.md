---
name: rewrite-history
description: >
  Rewrite git history across one or many repos: collapse author/committer identities via mailmap,
  strip AI co-author trailers (Claude / Codex / Bots / Manus / Copilot / Dependabot / github-actions),
  purge path globs, then force-push heads + tags + LFS and edit release notes. Includes a pre-phase
  to commit/rebase/push any outstanding work on workstations, and a post-phase to reset every
  workstation clone to the rewritten origin.
  Use when the user asks to "clean up commit authors", "remove AI co-authors from history",
  "strip Claude/Codex trailers", "collapse identities with a mailmap", "rewrite history for all
  my repos", or "force-push everywhere and update my other machines".
---

# Rewrite History

End-to-end git history rewrite + workstation sync across multiple repos.

## When to use

Triggers:
- "rewrite history", "clean up commit history"
- "strip Co-authored-by Claude/Codex/etc."
- "collapse/dedupe commit authors", "apply a mailmap to all my repos"
- "force-push everywhere and update my workstations"
- "delete extras" in the context of commit identities

Skip for:
- Single-commit amends (use plain `git commit --amend` or `git rebase -i`)
- Cosmetic commit-message edits on unreachable commits (not worth the force-push churn)

## Prerequisites

- `git`, `gh`, `ssh`, `python3`, `git-filter-repo` (install: `curl -fsSL https://raw.githubusercontent.com/newren/git-filter-repo/main/git-filter-repo -o ~/.local/bin/git-filter-repo && chmod +x ~/.local/bin/git-filter-repo`)
- SSH access to `github.com` via keys
- Enough disk for mirror clones (large LFS-heavy repos can be multi-GB — use a real filesystem, **not tmpfs**)
- For workstation sync: SSH aliases configured for each Linux/Mac host; PowerShell on each Windows box; DevDrive-aware scanning for Windows (WSL cannot read ReFS DevDrive)

## Scripts

All in `scripts/` next to this file:

| Script | Purpose |
|---|---|
| `mailmap.example` | Template mailmap showing identity-collapse rules. Copy + edit per job. |
| `callback.py` | `git-filter-repo --commit-callback` body. Strips AI co-author trailer lines. |
| `dryrun.py` | Fresh-clone each repo → scan → render a markdown report of proposed changes. No push. |
| `pipeline.sh` | Full pipeline per repo: clone → LFS fetch → filter-repo → restore origin → LFS push → force-push heads + tags → edit release notes. Runs all repos in parallel. |
| `sync-host.sh` / `sync-host.ps1` | Per-host pre-rewrite: commit dirty trees, `git pull --rebase`, push. Leaves working trees clean. |
| `pull-host.sh` / `pull-host.ps1` | Per-host post-rewrite: fetch origin, `git reset --hard origin/<branch>`. Skips dirty/detached/no-upstream clones. |
| `orchestrate-sync.sh` / `orchestrate-pull.sh` | Fan out sync / pull scripts to reachable Linux hosts via SSH + alex-pc locally (WSL + Windows via `powershell.exe`). Logs per-host. |

## Workflow

### 0. Scope

Confirm with user:
- Which repos (hardcoded list, `gh repo list <owner>` filtered by `isFork=false isArchived=false`, or specific subset).
- Which identities to collapse (collect authors with `git shortlog -sen --branches` per repo; user decides yes/no per identity).
- Path globs to purge (if any, e.g. `*.arw` in CRAP).
- Which workstations to touch (check `~/CRAP/_config/workstations.yaml` or equivalent).

### 1. Build mailmap + callback

Copy `scripts/mailmap.example` to working dir, edit with the collapse rules. Standard git mailmap format:
```
Proper Name <proper@email> <old@email>
Proper Name <proper@email> Old Name <old@email>
```

`scripts/callback.py` covers the AI-trailer regex for commits — edit the target list if needed.

### 2. Pre-rewrite workstation sync

Run `orchestrate-sync.sh` against all reachable hosts. This commits dirty trees with `auto: pre-rewrite snapshot <date>`, runs `git pull --rebase`, pushes local-only commits. Inform user of:
- Any rebase conflicts (the script doesn't auto-resolve).
- Any push failures.
- Which hosts were unreachable (handle manually).

If anything was pushed to GitHub during this phase, the mirrors built in step 3 will pick it up because clones are fresh.

### 3. Dry-run report

Run `dryrun.py <report.md>` to fresh-clone every target repo + generate a markdown report with per-repo before/after author counts, trailer counts, release-note hits. Save the report into the user's notes (e.g. Obsidian Inbox) for their review.

Wait for user approval before the force-push phase.

### 4. Full pipeline (pull → rewrite → force-push)

Run `pipeline.sh`. Parallel per-repo: fresh clone, LFS fetch, filter-repo with `--mailmap` + `--commit-callback` (plus any `--path-glob --invert-paths` purges), LFS push, force-push `refs/heads/*` and `refs/tags/*`, edit matching release-note bodies via `gh release edit --notes`.

**Do not pass `--refs` to filter-repo when using `--mailmap`** — that combination silently drops the mailmap. Rewrite all refs, then selectively push only heads + tags.

### 5. Post-rewrite workstation pull

Run `orchestrate-pull.sh REPOS=...` to reset every matching clone to `origin/<current-branch>`. Skips dirty, detached-HEAD, and no-upstream clones. Safe to re-run.

### 6. Report residuals

Things that need human follow-up:
- Clones that were skipped for dirt/detached/no-upstream state.
- Submodule pointer changes that weren't caught by the main-tree dirty check.
- Unreachable workstations (mac without ssh alias, Windows without OpenSSH Server, external-collaborator boxes).

## Known gotchas

- **DevDrive cannot be accessed from WSL.** On Windows hosts with ReFS DevDrives, you must use `powershell.exe` (native) to scan them. `pull-host.ps1` enumerates drives via `Get-Partition` and walks all assigned mount paths.
- **`git fetch --all` recurses into submodule remotes.** A 403 on a submodule's origin kills the fetch and blocks the reset. The pull scripts use `git -c fetch.recurseSubmodules=no fetch origin` to avoid this.
- **Tag push via a bash loop is slow** (one SSH round-trip per tag). For repos with many tags prefer `git push --force origin refs/tags/*:refs/tags/*` in a single push.
- **GitHub commit search indexes only the default branch**, so `/search?type=commits` counts will not match a local `git log --branches` scan. Don't use search URLs to validate the rewrite scope.
- **`git filter-repo --refs refs/heads/` + `--mailmap` silently no-ops the mailmap.** Drop `--refs`; apply to all refs; push only heads + tags.
- **Archived repos reject pushes.** Either skip them, or unarchive → push → re-archive round-trip.
- **Large LFS repos are network-bound.** A 4GB LFS push can take 15+ minutes regardless of script efficiency.

## Related

- `plugins/develop/scripts/cleanup-checkins.sh` — single-repo ancestor of this skill. Kept for reference.
