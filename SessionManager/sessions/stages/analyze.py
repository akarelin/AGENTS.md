"""Analyze stage — run session-intel's batch-extract + llm-analyze (ollama)
for each record in state='named', producing a structured markdown summary
at ~/_/{internals}/session-intel/analyzed/{source}/<tool>-<date>-<id12>.md.

Strategy:
  1. Group eligible records by (source, agent_or_project) so we can run
     batch-extract once per dir.
  2. For each group: run batch-extract.py → writes .prompt.md into a
     working dir, then run llm-analyze.py --backend=ollama over it.
  3. After, scan the analyzed output dir and attach analyzed_md path
     to each record; transition to 'analyzed'.

Idempotent: batch-extract & llm-analyze both support --skip-existing.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from ..llm import record_tokens
from ..orchestrator import StageResult
from ..store import SessionStore


from .. import skill_paths

BATCH_EXTRACT = str(skill_paths.script("session-intel", "scripts", "batch-extract.py"))
LLM_ANALYZE = str(skill_paths.script("session-intel", "scripts", "llm-analyze.py"))

# Where session-intel's output lands (matches existing layout)
ANALYZED_BASE = Path("/Users/alex/_/{internals}/session-intel/analyzed")
# Where we stage .prompt.md files (separated from the canonical intel dir so
# we don't pollute it if the user inspects manually)
PROMPTS_BASE = Path("/tmp/sessionskills/prompts")


def _run(cmd: list[str], timeout: int = 3600) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def _ensure_prompts_for(source: str, input_dir: Path, prompts_dir: Path) -> int:
    """Run batch-extract.py to populate .prompt.md files. Returns processed count."""
    prompts_dir.mkdir(parents=True, exist_ok=True)
    rc, out, err = _run([
        "python3", BATCH_EXTRACT,
        "--source", "openclaw" if source == "openclaw" else "claude-code",
        "--input", str(input_dir),
        "--output", str(prompts_dir),
        "--skip-existing",
    ])
    if rc != 0:
        print(f"[analyze] batch-extract rc={rc} err={err[-300:]}")
    return rc


def _run_llm_analyze(prompts_dir: Path, analyzed_dir: Path,
                     host: str, model: str, limit: int | None) -> int:
    analyzed_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "python3", LLM_ANALYZE,
        "--input", str(prompts_dir),
        "--output", str(analyzed_dir),
        "--backend", "ollama",
        "--ollama-host", host,
        "--model", model,
        "--skip-existing",
    ]
    if limit:
        cmd.extend(["--limit", str(limit)])
    env = os.environ.copy()
    env.setdefault("GEMINI_API_KEY", "notneeded")  # gemini lazy-imported; harmless
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=14400, env=env)
    if proc.returncode != 0:
        print(f"[analyze] llm-analyze rc={proc.returncode} stderr={proc.stderr[-300:]}")
    return proc.returncode


def _load_token_log(analyzed_dir: Path) -> dict[str, dict]:
    """Read ollama-tokens.jsonl emitted by llm-analyze.py. Returns
    {output_filename: {'prompt_eval_count':..., 'eval_count':..., 'model':...}}.
    Empty dict if the sidecar is missing or unreadable."""
    log = analyzed_dir / "ollama-tokens.jsonl"
    out: dict[str, dict] = {}
    if not log.exists():
        return out
    try:
        with log.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                name = row.get("output_file")
                if name:
                    # Keep only the most recent entry per file (file is append-only
                    # across runs; later wins).
                    out[name] = row
    except OSError:
        pass
    return out


def _find_analyzed(rec_source: str, rec_source_id: str) -> Path | None:
    """Match the output filename pattern <tool>-<date>-<id12>.md."""
    tool = "openclaw" if rec_source == "openclaw" else "claude-code"
    id12 = rec_source_id[:12]
    adir = ANALYZED_BASE / tool
    if not adir.is_dir():
        return None
    # Filenames: <tool>-<date>-<id12>.md
    for f in adir.glob(f"{tool}-*-{id12}.md"):
        return f
    return None


def run(store: SessionStore, cfg: dict, *,
        limit: int | None = None,
        dry_run: bool = False,
        force: bool = False,
        source: str | None = None,
        source_id: str | None = None,
        **_: object) -> StageResult:
    result = StageResult(stage="analyze")

    host = cfg["llm"]["host"]
    model = cfg["llm"]["model_chat"]

    eligible = ["named", "orphan_snapshot"] if not force \
        else ["named", "orphan_snapshot", "analyzed"]
    records = store.select_by_state(eligible, limit=limit, source=source)
    if not records:
        return result

    # Group inputs by source+agent/project so we minimize batch-extract runs
    groups: dict[tuple[str, str], list] = {}
    for rec in records:
        if source_id is not None and rec.source_id != source_id:
            continue
        if rec.source == "openclaw" and rec.agent:
            key = ("openclaw", rec.agent)
        elif rec.source == "claude-code" and rec.project:
            key = ("claude-code", rec.project)
        else:
            continue
        groups.setdefault(key, []).append(rec)

    if dry_run:
        for (src, tgt), recs in groups.items():
            print(f"[analyze] would process {len(recs)} records from {src}/{tgt}")
            result.processed += len(recs)
        return result

    # Per group: run extract + analyze
    for (src, tgt), recs in groups.items():
        if src == "openclaw":
            input_dir = Path.home() / ".openclaw" / "agents" / tgt / "sessions"
        else:
            input_dir = Path.home() / ".claude" / "projects" / tgt
        if not input_dir.is_dir():
            result.errors += len(recs)
            continue

        prompts_dir = PROMPTS_BASE / src / tgt
        analyzed_dir = ANALYZED_BASE / src

        print(f"[analyze] extracting prompts: {src}/{tgt} ({len(recs)} records)")
        if _ensure_prompts_for(src, input_dir, prompts_dir) != 0:
            result.errors += len(recs)
            continue

        print(f"[analyze] running ollama analyze: {src}/{tgt}")
        _run_llm_analyze(prompts_dir, analyzed_dir, host, model, limit=None)

        token_log = _load_token_log(analyzed_dir)

        # Update records
        for rec in recs:
            analyzed = _find_analyzed(rec.source, rec.source_id)
            if analyzed and analyzed.exists():
                rec.paths["analyzed_md"] = str(analyzed)
                meta = token_log.get(analyzed.name)
                if meta:
                    record_tokens(rec, "analyze", meta)
                rec.transition("analyzed", stage="analyze", notes=analyzed.name)
                store.upsert(rec)
                result.processed += 1
            else:
                # batch-extract skipped (too few messages) — still advance state
                rec.transition("analyzed", stage="analyze", notes="skipped-by-session-intel")
                store.upsert(rec)
                result.skipped += 1

    return result
