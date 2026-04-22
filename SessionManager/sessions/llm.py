"""Local LLM client (Ollama) + cloud fallback.

Stages call `get_llm(cfg)` which returns the first available backend from:
  1. LocalLLM (Ollama at cfg.llm.host)
  2. CloudLLM (Vertex/Anthropic via env)
  3. HeuristicOnly (raises on generate, used to gate caller into heuristic path)

Install:
    brew install ollama
    brew services start ollama
    ollama pull qwen3:8b           # or whichever tag user picks
    ollama pull nomic-embed-text
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class LLMUnavailable(RuntimeError):
    pass


def record_tokens(rec, stage: str, meta: dict) -> None:
    """Persist an Ollama call's token counts onto a SessionRecord.

    Accumulates across repeated calls (e.g. analyze invoked twice) so the
    per-stage numbers stay a running total. `sm-pipeline stats` aggregates
    via json_extract over classification.ollama_tokens."""
    if not meta:
        return
    bucket = rec.classification.setdefault("ollama_tokens", {})
    cur = bucket.setdefault(stage, {"prompt": 0, "eval": 0, "calls": 0,
                                    "total_duration_ns": 0})
    cur["prompt"] += int(meta.get("prompt_eval_count") or 0)
    cur["eval"] += int(meta.get("eval_count") or 0)
    cur["calls"] += 1
    cur["total_duration_ns"] += int(meta.get("total_duration_ns") or 0)
    if meta.get("model") and "model" not in cur:
        cur["model"] = meta["model"]


class LocalLLM:
    """Ollama HTTP client. No external deps beyond urllib."""

    def __init__(self, host: str = "http://127.0.0.1:11434",
                 model: str = "qwen3:8b",
                 embed_model: str = "nomic-embed-text",
                 timeout: int = 120):
        self.host = host.rstrip("/")
        self.model = model
        self.embed_model = embed_model
        self.timeout = timeout

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=3) as r:
                data = json.load(r)
                return bool(data.get("models"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            return False

    def list_models(self) -> list[str]:
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=3) as r:
                return [m["name"] for m in json.load(r).get("models", [])]
        except Exception:
            return []

    def generate(self, prompt: str, system: str | None = None,
                 temperature: float = 0.3, format_json: bool = False,
                 return_meta: bool = False) -> str | tuple[str, dict]:
        """Generate text. When return_meta=True, returns (text, meta) where
        meta carries Ollama's `prompt_eval_count` + `eval_count` + `total_duration`
        (ns) for token-budget telemetry. Also stored on self.last_meta for the
        fire-and-forget case."""
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        if format_json:
            payload["format"] = "json"
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.load(r)
        except (urllib.error.URLError, OSError) as e:
            raise LLMUnavailable(f"ollama generate failed: {e}") from e
        meta = {
            "prompt_eval_count": int(data.get("prompt_eval_count") or 0),
            "eval_count": int(data.get("eval_count") or 0),
            "total_duration_ns": int(data.get("total_duration") or 0),
            "model": self.model,
        }
        self.last_meta = meta
        text = data.get("response", "")
        return (text, meta) if return_meta else text

    def embed(self, text: str) -> list[float]:
        payload = {"model": self.embed_model, "prompt": text}
        req = urllib.request.Request(
            f"{self.host}/api/embeddings",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.load(r)["embedding"]
        except (urllib.error.URLError, OSError) as e:
            raise LLMUnavailable(f"ollama embed failed: {e}") from e


class CloudLLM:
    """Stub — wire to the existing sm-local.py Vertex/Anthropic client.

    Factored out later; for now, available() returns False unless env is set.
    """

    def __init__(self, provider: str = "anthropic-vertex"):
        self.provider = provider

    def available(self) -> bool:
        if self.provider == "anthropic-vertex":
            return bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")) or \
                   bool(os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID"))
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def generate(self, prompt: str, system: str | None = None, **_: Any) -> str:
        raise LLMUnavailable("cloud backend not yet wired — use local Ollama")

    def embed(self, text: str) -> list[float]:
        raise LLMUnavailable("cloud embed not yet wired")


def get_llm(cfg: dict) -> LocalLLM | CloudLLM | None:
    """Return the first available backend, or None if no backend is up.

    Stages handle None according to their policy: heuristic fallback (name),
    skip-this-pass (analyze), or run-regardless (cluster).
    """
    local = LocalLLM(
        host=cfg["llm"]["host"],
        model=cfg["llm"]["model_chat"],
        embed_model=cfg["llm"]["model_embed"],
    )
    if local.available():
        return local
    fallback = cfg["llm"].get("fallback", "cloud")
    if fallback == "cloud":
        cloud = CloudLLM(cfg["llm"].get("cloud_provider", "anthropic-vertex"))
        if cloud.available():
            return cloud
    return None
