"""Minimal HITL review TUI.

v1: plain stdin/stdout — stays dependency-free (no Textual).
v2: promote to Textual TUI that matches sm-tui.py styling.

Iterates pending items in ~/.sessionskills/review_queue.json.
For each: prints context, asks y/n/e/s/q; persists decision.

Kind-specific handlers:
  • unlinked_project  — Track 2 §2.5 — let reviewer pick/create a canonical
                        project and stamp it on the record.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from . import config as cfgmod
from . import projects as projmod
from .store import SessionStore


def _atomic_write(path: Path, data: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".review-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        os.unlink(tmp)
        raise


def _show_item(item: dict, store: SessionStore) -> None:
    print("=" * 70)
    print(f"Kind:       {item.get('kind')}")
    print(f"Confidence: {item.get('confidence')}")
    print(f"Proposal:   {json.dumps(item.get('proposal', {}), indent=2)}")
    for rid in item.get("record_ids", []):
        source, sid = rid.split(":", 1)
        rec = store.get(source, sid)
        if rec:
            print(f"\n{rid}  agent={rec.agent} project={rec.project} state={rec.state}")
            print(f"  started: {rec.started_at} model: {rec.model} turns: {rec.turn_count}")
            if "raw_jsonl" in rec.paths:
                print(f"  raw: {rec.paths['raw_jsonl']}")
            if "analyzed_md" in rec.paths:
                print(f"  analyzed: {rec.paths['analyzed_md']}")
    print("-" * 70)


def _now_iso() -> str:
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_new_project(project_id: str, name: str, aliases: list[str]) -> bool:
    """Append a minimal new project entry at the end of _registry.yaml.
    Keeps existing comments + structure intact (pure text append)."""
    path = projmod.REGISTRY_PATH
    alias_yaml = ", ".join(f'"{a}"' for a in aliases) if aliases else ""
    block = (
        f"\n  - id: {project_id}\n"
        f"    name: {json.dumps(name)}\n"
        f"    aliases: [{alias_yaml}]\n"
        f"    claude_code_slugs: []\n"
        f"    openclaw_agents: []\n"
        f"    work_atom_slug: null\n"
        f"    langfuse_tag: project:{project_id}\n"
        f"    obsidian_page: null\n"
    )
    try:
        with open(path, "a") as f:
            f.write(block)
        return True
    except OSError as e:
        print(f"  ! failed to update registry: {e}")
        return False


def _stamp_canonical(store: SessionStore, record_ids: list[str],
                     canonical: str, task_id: str | None = None) -> int:
    proj = projmod.find_by_id(canonical)
    updated = 0
    for rid in record_ids:
        source, sid = rid.split(":", 1)
        rec = store.get(source, sid)
        if rec is None:
            continue
        rec.classification["canonical_project"] = canonical
        if proj:
            rec.classification["canonical_project_name"] = proj.name
        if task_id:
            rec.classification["task_id"] = task_id
        store.upsert(rec)
        updated += 1
    return updated


def _handle_unlinked_project(item: dict, store: SessionStore) -> str:
    """Return one of: 'accepted' / 'rejected' (ignored) / 'skip' / 'quit'."""
    projects = projmod.load_registry(force=True)
    print(f"\nRegistered projects ({len(projects)}): "
          + ", ".join(p.id for p in projects))
    print("Commands: [p]ick existing  [n]ew project  [i]gnore  [s]kip  [q]uit")

    while True:
        try:
            ans = input("> ").strip().lower()
        except EOFError:
            return "quit"
        if ans in ("p", "n", "i", "s", "q"):
            break
        print("(p/n/i/s/q)")

    if ans == "q":
        return "quit"
    if ans == "s":
        return "skip"
    if ans == "i":
        return "rejected"
    if ans == "p":
        try:
            pid = input("project id: ").strip()
        except EOFError:
            return "skip"
        if not pid:
            return "skip"
        if not projmod.find_by_id(pid):
            print(f"  ! no such project: {pid}")
            return "skip"
        n = _stamp_canonical(store, item.get("record_ids", []), pid)
        item["proposal"] = {"canonical_project": pid}
        print(f"  ✓ stamped {n} record(s) with canonical_project={pid}")
        return "accepted"
    if ans == "n":
        try:
            pid = input("new project id (short, snake/kebab, no slashes): ").strip()
            name = input("name (human-readable): ").strip() or pid
            raw_al = input("comma-separated aliases (optional): ").strip()
        except EOFError:
            return "skip"
        if not pid:
            return "skip"
        if projmod.find_by_id(pid):
            print(f"  ! project id already exists: {pid}")
            return "skip"
        aliases = [a.strip() for a in raw_al.split(",") if a.strip()] if raw_al else []
        if not _append_new_project(pid, name, aliases):
            return "skip"
        projmod.load_registry(force=True)
        n = _stamp_canonical(store, item.get("record_ids", []), pid)
        item["proposal"] = {"canonical_project": pid}
        print(f"  ✓ created project {pid!r} and stamped {n} record(s)")
        return "accepted"
    return "skip"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sm-review")
    ap.add_argument("--config", default=None)
    ap.add_argument("--notify", action="store_true",
                    help="Only report pending count (for launchd reminder)")
    args = ap.parse_args(argv)

    cfg = cfgmod.load(args.config)
    queue_path = Path(cfgmod.expand(cfg["store"]["review_queue"]))
    store = SessionStore(cfgmod.expand(cfg["store"]["path"]))

    if not queue_path.exists():
        print("no review queue — nothing to do")
        return 0

    with open(queue_path) as f:
        queue = json.load(f)

    pending = [it for it in queue["items"] if it.get("status") == "pending"]
    total = len(pending)
    if total == 0:
        print("no pending review items")
        return 0

    if args.notify:
        print(f"{total} items pending review — run `sm-review` to process")
        return 0

    print(f"{total} pending items.")
    done = 0
    for item in pending:
        print(f"\n[{done+1}/{total}]")
        _show_item(item, store)

        kind = item.get("kind")

        if kind == "unlinked_project":
            verdict = _handle_unlinked_project(item, store)
            if verdict == "quit":
                break
            if verdict == "skip":
                done += 1
                continue
            item["status"] = verdict  # accepted | rejected
            item["decision_at"] = _now_iso()
            _atomic_write(queue_path, queue)
            done += 1
            continue

        # Default y/n/e/s/q handler
        print("Commands: [y]accept [n]reject [e]dit [s]kip [q]uit")
        while True:
            try:
                ans = input("> ").strip().lower()
            except EOFError:
                ans = "q"
            if ans in ("y", "n", "e", "s", "q"):
                break
            print("(y/n/e/s/q)")

        if ans == "q":
            break
        if ans == "s":
            done += 1
            continue
        if ans == "y":
            item["status"] = "accepted"
            item["decision_at"] = _now_iso()
        elif ans == "n":
            item["status"] = "rejected"
            item["decision_at"] = _now_iso()
        elif ans == "e":
            print(f"current proposal: {json.dumps(item.get('proposal', {}))}")
            edited = input("paste new proposal JSON (empty=cancel): ").strip()
            if edited:
                try:
                    item["proposal"] = json.loads(edited)
                    item["status"] = "edited"
                except json.JSONDecodeError as e:
                    print(f"bad JSON: {e}; keeping pending")
                    continue

        _atomic_write(queue_path, queue)
        done += 1

    print(f"\nprocessed {done} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
