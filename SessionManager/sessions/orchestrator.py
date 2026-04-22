"""Stage registry + DAG runner.

CLI:
    sm-pipeline doctor                       # health check
    sm-pipeline run <stage> [<stage>...]     # invoke stages in order
    sm-pipeline run <pipeline-name>          # run a named pipeline from config
    sm-pipeline run ingest --dry-run
    sm-pipeline stats                        # count by state

Stages are modules under sessions.stages.<name> exporting:
    def run(store, cfg, *, limit=None, dry_run=False, force=False,
            source=None, source_id=None) -> StageResult
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from . import config as cfgmod
from .llm import LocalLLM, get_llm
from .store import SessionStore


@dataclass
class StageResult:
    stage: str
    processed: int = 0
    skipped: int = 0
    errors: int = 0
    to_review: int = 0

    def fmt(self) -> str:
        return (f"[{self.stage}] processed={self.processed} skipped={self.skipped} "
                f"errors={self.errors} to_review={self.to_review}")


KNOWN_STAGES = (
    "ingest", "merge", "name", "analyze",
    "write_to_memory", "cluster", "classify",
    "prune", "archive", "review",
)


def cmd_doctor(cfg: dict) -> int:
    print(f"config:       {cfg['_path']}")
    store_path = cfgmod.expand(cfg["store"]["path"])
    store = SessionStore(store_path)
    print(f"store:        {store_path}")
    counts = store.count_by_state()
    print(f"  records:    {store.count()}")
    for state, n in sorted(counts.items()):
        print(f"    {state:<18} {n}")

    print(f"\nllm.host:     {cfg['llm']['host']}")
    print(f"llm.model:    {cfg['llm']['model_chat']}")
    local = LocalLLM(host=cfg['llm']['host'],
                     model=cfg['llm']['model_chat'],
                     embed_model=cfg['llm']['model_embed'])
    if local.available():
        print(f"  ollama:     OK")
        print(f"  models:     {', '.join(local.list_models()) or '(none)'}")
        try:
            out = local.generate("Say 'OK' and nothing else.", temperature=0)
            print(f"  test gen:   {out.strip()[:60]!r}")
        except Exception as e:
            print(f"  test gen:   FAIL — {e}")
    else:
        print(f"  ollama:     UNAVAILABLE (run `brew services start ollama`)")
        fb = get_llm(cfg)
        if fb:
            print(f"  fallback:   {type(fb).__name__}")
        else:
            print(f"  fallback:   NONE — name/classify will use heuristic; analyze will skip")

    # Symlink health — ~/.claude/{projects,plans} live behind symlinks into
    # Synology-synced SD/. Dangling targets cause silent write failures.
    print("\nsymlinks:")
    for link in (Path.home() / ".claude" / "projects",
                 Path.home() / ".claude" / "plans"):
        if not link.is_symlink():
            print(f"  {link}: NOT A SYMLINK")
            continue
        tgt = Path(os.readlink(link))
        status = "OK" if tgt.is_dir() else "MISSING (run scripts/ensure-claude-symlinks.sh)"
        print(f"  {link} -> {tgt}  {status}")
    return 0


def cmd_stats(cfg: dict) -> int:
    store = SessionStore(cfgmod.expand(cfg["store"]["path"]))
    counts = store.count_by_state()
    print(f"total: {store.count()}")
    for state, n in sorted(counts.items()):
        print(f"  {state:<18} {n}")

    # Token telemetry rolled up from classification.ollama_tokens (populated
    # by record_tokens in sessions.llm). Silent when no calls recorded.
    import sqlite3
    conn = sqlite3.connect(store.path)
    try:
        rows = conn.execute(
            "SELECT json_extract(json, '$.classification.ollama_tokens') AS t "
            "FROM records "
            "WHERE json_extract(json, '$.classification.ollama_tokens') IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()
    if rows:
        agg: dict[str, dict] = {}
        for (raw,) in rows:
            if not raw:
                continue
            try:
                bucket = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue
            for stage, m in bucket.items():
                a = agg.setdefault(stage, {"prompt": 0, "eval": 0,
                                           "calls": 0, "records": 0})
                a["prompt"] += int(m.get("prompt") or 0)
                a["eval"] += int(m.get("eval") or 0)
                a["calls"] += int(m.get("calls") or 0)
                a["records"] += 1
        if agg:
            print("\nollama tokens (by stage):")
            print(f"  {'stage':<16} {'records':>8} {'calls':>8} "
                  f"{'prompt':>12} {'eval':>12}")
            for stage, a in sorted(agg.items()):
                print(f"  {stage:<16} {a['records']:>8} {a['calls']:>8} "
                      f"{a['prompt']:>12,} {a['eval']:>12,}")
    return 0


def cmd_run(cfg: dict, stages: list[str], **kwargs) -> int:
    # Expand pipeline names
    expanded: list[str] = []
    for s in stages:
        if s in cfg.get("pipeline", {}):
            expanded.extend(cfg["pipeline"][s])
        elif s in KNOWN_STAGES:
            expanded.append(s)
        else:
            print(f"unknown stage or pipeline: {s}", file=sys.stderr)
            return 2

    store = SessionStore(cfgmod.expand(cfg["store"]["path"]))
    rc = 0
    for stage_name in expanded:
        try:
            mod = importlib.import_module(f"sessions.stages.{stage_name}")
        except ImportError as e:
            print(f"[{stage_name}] NOT YET IMPLEMENTED ({e})")
            rc = 1
            continue
        try:
            result: StageResult = mod.run(store, cfg, **kwargs)
        except Exception as e:
            print(f"[{stage_name}] ERROR: {e}", file=sys.stderr)
            rc = 1
            continue
        print(result.fmt())
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sm-pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="Health check: config, store, ollama")
    sub.add_parser("stats", help="Record counts by state")

    mp = sub.add_parser("migrate-skills",
                        help="Migrate ~/_/{internals}/Skills → SD.agents/skills/ (safe, manifest-backed)")
    mp.add_argument("--apply", action="store_true",
                    help="actually move files (default: dry-run)")
    mp.add_argument("--rewrite-refs", action="store_true",
                    help="also rewrite openclaw.json + .lobster hardcoded paths (needs --apply)")

    rp = sub.add_parser("run", help="Run one or more stages")
    rp.add_argument("stages", nargs="+", help="stage name(s) or pipeline name from config")
    rp.add_argument("--dry-run", action="store_true")
    rp.add_argument("--force", action="store_true")
    rp.add_argument("--limit", type=int, default=None)
    rp.add_argument("--source", default=None, help="restrict to one source")
    rp.add_argument("--source-id", default=None, help="restrict to one source_id")
    rp.add_argument("--backfill", action="store_true",
                    help="ingest: include all historical (incl. Langfuse pull)")
    rp.add_argument("--reconcile-only", action="store_true",
                    help="name: skip subprocess, just scan symlinks and update store")

    ap.add_argument("--config", default=None, help="path to sessionskills.yaml")
    args = ap.parse_args(argv)

    cfg = cfgmod.load(args.config)

    if args.cmd == "doctor":
        return cmd_doctor(cfg)
    if args.cmd == "stats":
        return cmd_stats(cfg)
    if args.cmd == "migrate-skills":
        from .migrate_skills import cmd_migrate_skills
        return cmd_migrate_skills(apply=args.apply, rewrite=args.rewrite_refs)
    if args.cmd == "run":
        return cmd_run(
            cfg,
            args.stages,
            limit=args.limit,
            dry_run=args.dry_run,
            force=args.force,
            source=args.source,
            source_id=args.source_id,
            backfill=args.backfill,
            reconcile_only=args.reconcile_only,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
