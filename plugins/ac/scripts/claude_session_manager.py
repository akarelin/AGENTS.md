#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
CLAUDE_PROJECTS = CLAUDE_DIR / "projects"
DEFAULT_MAP_PATH = Path(__file__).with_name("claude_session_map.json")
SESSION_SENTINEL_NAMES = (
  "messages.json",
  "history.json",
  "session.json",
  "transcript.json",
)

# Put constants at the top.
NON_REPO_PREFIXES = (
  str(Path.home() / "Downloads"),
)


def load_map(map_path: Path) -> dict[str, str]:
  with map_path.open("r", encoding="utf-8") as f:
    data = json.load(f)
  if not isinstance(data, dict):
    raise ValueError(f"Expected JSON object in {map_path}")
  return {str(k): str(v) for k, v in data.items()}


def ensure_dir(path: Path) -> None:
  path.mkdir(parents=True, exist_ok=True)


def remove_path(path: Path) -> None:
  if not path.exists() and not path.is_symlink():
    return
  if path.is_symlink() or path.is_file():
    path.unlink()
    return
  shutil.rmtree(path)


def symlink_dir(link_path: Path, target: Path) -> None:
  ensure_dir(link_path.parent)
  remove_path(link_path)
  os.symlink(str(target), str(link_path), target_is_directory=True)


def repo_target(repo_root: str, session_name: str) -> Path:
  target = Path(repo_root).expanduser() / ".claude" / session_name
  ensure_dir(target)
  return target.resolve()


def repo_exists(repo_root: str) -> bool:
  return Path(repo_root).exists()


def git_root(path: Path) -> Path | None:
  probe = path.resolve()
  if probe.is_file():
    probe = probe.parent
  while True:
    if (probe / ".git").exists():
      return probe
    if probe.parent == probe:
      return None
    probe = probe.parent


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
  return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, check=check)


def cmd_sync(args: argparse.Namespace) -> int:
  mapping = load_map(args.map)
  ensure_dir(CLAUDE_PROJECTS)
  for session_name, repo_root in mapping.items():
    if not repo_exists(repo_root):
      print(f"skip missing repo path: {repo_root}", file=sys.stderr)
      continue
    target = repo_target(repo_root, session_name)
    link_path = CLAUDE_PROJECTS / session_name
    symlink_dir(link_path, target)
    print(f"{link_path} -> {target}")
  return 0


def pull_repo(repo_root: str) -> int:
  root = git_root(Path(repo_root))
  if not root:
    print(f"skip non-git path: {repo_root}")
    return 0
  print(f"pull {root}")
  run(["git", "pull", "--rebase", "--autostash"], cwd=root)
  return 0


def push_repo(repo_root: str, message: str) -> int:
  root = git_root(Path(repo_root))
  if not root:
    print(f"skip non-git path: {repo_root}")
    return 0
  status = subprocess.run(["git", "status", "--porcelain"], cwd=root, text=True, capture_output=True, check=True)
  if not status.stdout.strip():
    print(f"clean {root}")
    return 0
  run(["git", "add", "-A"], cwd=root)
  run(["git", "commit", "-m", message], cwd=root)
  run(["git", "push"], cwd=root)
  print(f"pushed {root}")
  return 0


def cmd_pull_latest(args: argparse.Namespace) -> int:
  mapping = load_map(args.map)
  if args.all:
    roots = sorted(set(mapping.values()))
  else:
    roots = [mapping[args.session]]
  for repo_root in roots:
    if repo_exists(repo_root):
      pull_repo(repo_root)
  return 0


def list_sessions_for_repo(repo_root: str) -> list[tuple[str, Path]]:
  repo = Path(repo_root)
  d = repo / ".claude"
  out = []
  if d.is_dir():
    for child in sorted(d.iterdir(), key=lambda p: p.name.lower()):
      if child.is_dir():
        out.append((child.name, child))
  return out


def current_repo_from_cwd(mapping: dict[str, str]) -> str | None:
  cwd = Path.cwd().resolve()
  for repo_root in sorted(set(mapping.values()), key=len, reverse=True):
    p = Path(repo_root).resolve()
    try:
      cwd.relative_to(p)
      return repo_root
    except Exception:
      pass
  return None


def cmd_list(args: argparse.Namespace) -> int:
  mapping = load_map(args.map)
  if args.current:
    repo_root = current_repo_from_cwd(mapping)
    if not repo_root:
      print("current directory is not under a mapped repo", file=sys.stderr)
      return 1
    print(repo_root)
    for name, path in list_sessions_for_repo(repo_root):
      print(f"{name}\t{path}")
    return 0

  seen = set()
  for repo_root in sorted(set(mapping.values())):
    if repo_root in seen:
      continue
    seen.add(repo_root)
    repo = Path(repo_root)
    print(f"[{repo}]")
    for name, path in list_sessions_for_repo(repo_root):
      print(f"  {name}\t{path}")
  return 0


def cmd_resume(args: argparse.Namespace) -> int:
  mapping = load_map(args.map)
  if args.session not in mapping:
    print(f"unknown session: {args.session}", file=sys.stderr)
    return 1
  repo_root = Path(mapping[args.session]).expanduser()
  if args.exec:
    cmd = args.exec if isinstance(args.exec, list) else [args.exec]
    os.chdir(repo_root)
    os.execvp(cmd[0], cmd)
  print(repo_root)
  return 0


def is_empty_session_dir(path: Path) -> bool:
  if not path.is_dir():
    return False
  entries = list(path.iterdir())
  if not entries:
    return True
  files = [p for p in entries if p.is_file()]
  dirs = [p for p in entries if p.is_dir()]
  if dirs:
    return False
  names = {p.name for p in files}
  if names and names.issubset({"README", ".gitkeep"}):
    return True
  if not any(name in names for name in SESSION_SENTINEL_NAMES) and all(p.stat().st_size == 0 for p in files):
    return True
  return False


def cmd_delete_empty(args: argparse.Namespace) -> int:
  mapping = load_map(args.map)
  deleted = 0
  for session_name, repo_root in mapping.items():
    target = repo_target(repo_root, session_name)
    if is_empty_session_dir(target):
      print(f"empty {target}")
      if args.apply:
        remove_path(target)
        link_path = CLAUDE_PROJECTS / session_name
        if link_path.is_symlink():
          link_path.unlink()
        deleted += 1
  print(f"deleted={deleted}")
  return 0


def cmd_rename(args: argparse.Namespace) -> int:
  mapping = load_map(args.map)
  if args.old not in mapping:
    print(f"unknown old session: {args.old}", file=sys.stderr)
    return 1
  if args.new in mapping:
    print(f"target session already exists: {args.new}", file=sys.stderr)
    return 1

  repo_root = mapping[args.old]
  old_target = repo_target(repo_root, args.old)
  new_target = Path(repo_root).expanduser() / ".claude" / args.new
  old_link = CLAUDE_PROJECTS / args.old
  new_link = CLAUDE_PROJECTS / args.new

  print(f"{old_target} -> {new_target}")
  if not args.apply:
    return 0

  if old_target.exists():
    old_target.rename(new_target)
  if old_link.exists() or old_link.is_symlink():
    remove_path(old_link)
  symlink_dir(new_link, new_target)

  del mapping[args.old]
  mapping[args.new] = repo_root
  with args.map.open("w", encoding="utf-8") as f:
    json.dump(mapping, f, indent=2, sort_keys=True)
    f.write("\n")
  return 0


def cmd_sync_all(args: argparse.Namespace) -> int:
  mapping = load_map(args.map)
  cmd_sync(args)
  roots = sorted(set(mapping.values()))
  for repo_root in roots:
    if repo_exists(repo_root):
      pull_repo(repo_root)
  for repo_root in roots:
    if repo_exists(repo_root):
      push_repo(repo_root, args.message)
  return 0


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(description="Claude session manager skill")
  p.add_argument("--map", type=Path, default=DEFAULT_MAP_PATH)

  sub = p.add_subparsers(dest="cmd", required=True)

  s = sub.add_parser("sync")
  s.set_defaults(func=cmd_sync)

  s = sub.add_parser("sync-all")
  s.add_argument("-m", "--message", default="checkpoint")
  s.set_defaults(func=cmd_sync_all)

  s = sub.add_parser("pull-latest")
  s.add_argument("--all", action="store_true")
  s.add_argument("session", nargs="?")
  s.set_defaults(func=cmd_pull_latest)

  s = sub.add_parser("list")
  s.add_argument("--current", action="store_true")
  s.set_defaults(func=cmd_list)

  s = sub.add_parser("resume")
  s.add_argument("session")
  s.add_argument("--exec", nargs="+")
  s.set_defaults(func=cmd_resume)

  s = sub.add_parser("delete-empty")
  s.add_argument("--apply", action="store_true")
  s.set_defaults(func=cmd_delete_empty)

  s = sub.add_parser("rename")
  s.add_argument("old")
  s.add_argument("new")
  s.add_argument("--apply", action="store_true")
  s.set_defaults(func=cmd_rename)

  return p


def main() -> int:
  parser = build_parser()
  args = parser.parse_args()
  if args.cmd == "pull-latest" and not args.all and not args.session:
    parser.error("pull-latest requires --all or a session")
  return args.func(args)


if __name__ == "__main__":
  raise SystemExit(main())
