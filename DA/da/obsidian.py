"""Obsidian vault operations — UI-agnostic.

Pure filesystem operations for reading, searching, and writing
Obsidian vault notes.  No Rich, no Textual — just pathlib + re.
"""

import datetime
import re
import yaml
from dataclasses import dataclass, field
from pathlib import Path

from da.config import Config

# Folders to skip when scanning
SKIP_DIRS = frozenset({
    ".obsidian", ".git", ".trash", ".github", ".vscode", ".claude", "{internals}",
})


# ── Data classes ──────────────────────────────────────────────────────

@dataclass
class NoteInfo:
    """Lightweight metadata about a single note."""
    path: Path
    name: str           # stem (no extension)
    folder: str         # relative parent folder ("Daily Notes", "KB/sub", ...)
    size: int
    mtime: float        # epoch
    mtime_str: str      # "2026-03-20 14:05"

    @property
    def mtime_short(self) -> str:
        return datetime.datetime.fromtimestamp(self.mtime).strftime("%m-%d")


@dataclass
class FolderInfo:
    """A vault folder with note count."""
    path: Path
    name: str
    note_count: int


@dataclass
class SearchResult:
    """A search hit."""
    note: NoteInfo
    context: str        # matching line snippet


@dataclass
class VaultTree:
    """Recursive folder/file structure for tree renderers."""
    path: Path
    name: str
    is_dir: bool
    note_count: int = 0         # only for dirs
    mtime_short: str = ""       # only for files
    children: list["VaultTree"] = field(default_factory=list)


@dataclass
class ProjectInfo:
    """A note with type: Project frontmatter."""
    path: Path
    name: str
    description: str
    status: str
    priority: str
    category: str
    owner_org: str
    tags: list[str]
    created: str
    updated: str
    folder: str       # relative parent folder


# ── Frontmatter ──────────────────────────────────────────────────────

def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from note content. Returns empty dict if none."""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end < 0:
        return {}
    try:
        return yaml.safe_load(content[3:end]) or {}
    except Exception:
        return {}


def list_projects(vault: Path) -> list[ProjectInfo]:
    """Find all notes with type: Project frontmatter."""
    projects: list[ProjectInfo] = []
    for p in _iter_notes(vault):
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        fm = parse_frontmatter(content)
        if fm.get("type") != "Project":
            continue
        try:
            rel = p.relative_to(vault)
            folder = str(rel.parent) if rel.parent != Path(".") else ""
        except ValueError:
            folder = ""
        tags = fm.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        projects.append(ProjectInfo(
            path=p,
            name=fm.get("name") or p.stem,
            description=fm.get("description", ""),
            status=fm.get("status", ""),
            priority=fm.get("priority", ""),
            category=fm.get("category", ""),
            owner_org=str(fm.get("owner_org", "")).replace("[[", "").replace("]]", "").strip('"'),
            tags=[t for t in tags if t],
            created=str(fm.get("created", "")),
            updated=str(fm.get("updated", "")),
            folder=folder,
        ))
    # Sort: active first, then by updated descending
    status_order = {"active": 0, "": 1, "on-hold": 2, "archived": 3}
    projects.sort(key=lambda p: (status_order.get(p.status, 1), p.updated or ""), reverse=False)
    projects.sort(key=lambda p: status_order.get(p.status, 1))
    return projects


# ── Helpers ───────────────────────────────────────────────────────────

def vault_path(cfg: Config) -> Path:
    """Resolve vault path from config."""
    raw = getattr(cfg, "obsidian_vault", None) or "~/_"
    return Path(raw).expanduser()


def is_md(p: Path) -> bool:
    return p.suffix.lower() == ".md" and not p.name.startswith(".")


def should_skip(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")


def extract_tags(content: str) -> list[str]:
    """Extract #tags from note content (not inside code blocks)."""
    cleaned = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    cleaned = re.sub(r"`[^`]+`", "", cleaned)
    return sorted(set(re.findall(r"(?:^|\s)#([A-Za-z][A-Za-z0-9_/-]*)", cleaned)))


def note_info(p: Path, vault: Path) -> NoteInfo:
    """Build NoteInfo for a single file."""
    stat = p.stat()
    try:
        rel = p.relative_to(vault)
        folder = str(rel.parent) if rel.parent != Path(".") else ""
    except ValueError:
        folder = ""
    return NoteInfo(
        path=p,
        name=p.stem,
        folder=folder,
        size=stat.st_size,
        mtime=stat.st_mtime,
        mtime_str=datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
    )


def _iter_notes(vault: Path):
    """Yield all .md files in vault, skipping hidden/internal dirs."""
    for p in vault.rglob("*.md"):
        if not is_md(p):
            continue
        try:
            parts = p.relative_to(vault).parts
        except ValueError:
            continue
        if any(should_skip(part) for part in parts):
            continue
        yield p


# ── Vault queries ─────────────────────────────────────────────────────

def list_folders(vault: Path) -> list[FolderInfo]:
    """Top-level folders with note counts."""
    folders = []
    for d in sorted(vault.iterdir()):
        if not d.is_dir() or should_skip(d.name):
            continue
        count = sum(1 for p in d.rglob("*.md") if is_md(p))
        if count > 0:
            folders.append(FolderInfo(path=d, name=d.name, note_count=count))
    return folders


def list_notes(folder: Path, vault: Path, recursive: bool = False) -> list[NoteInfo]:
    """Notes in a folder, sorted by mtime descending."""
    glob = folder.rglob("*.md") if recursive else folder.glob("*.md")
    notes = [note_info(p, vault) for p in glob if is_md(p)]
    notes.sort(key=lambda n: n.mtime, reverse=True)
    return notes


def recent_notes(vault: Path, limit: int = 20) -> list[NoteInfo]:
    """Most recently modified notes across the vault."""
    notes = [note_info(p, vault) for p in _iter_notes(vault)]
    notes.sort(key=lambda n: n.mtime, reverse=True)
    return notes[:limit]


def search(vault: Path, query: str, limit: int = 50) -> list[SearchResult]:
    """Search filenames then contents. Returns SearchResult list."""
    query_lower = query.lower()
    results: list[SearchResult] = []

    for p in _iter_notes(vault):
        # Filename match
        if query_lower in p.stem.lower():
            results.append(SearchResult(
                note=note_info(p, vault),
                context=f"[name match] {p.stem}",
            ))
            if len(results) >= limit:
                break
            continue

        # Content match
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if query_lower in content.lower():
                ctx = ""
                for line in content.split("\n"):
                    if query_lower in line.lower():
                        ctx = line.strip()[:100]
                        break
                results.append(SearchResult(note=note_info(p, vault), context=ctx))
                if len(results) >= limit:
                    break
        except Exception:
            continue

    return results


def read_note(path: Path) -> str:
    """Read note content."""
    return path.read_text(encoding="utf-8", errors="replace")


def write_note(path: Path, content: str) -> None:
    """Write note content back to file."""
    path.write_text(content, encoding="utf-8")


def vault_tree(vault: Path, max_depth: int = 4) -> VaultTree:
    """Build a recursive VaultTree structure for the entire vault."""

    def _build(dirpath: Path, depth: int) -> VaultTree:
        children: list[VaultTree] = []
        if depth >= max_depth:
            return VaultTree(path=dirpath, name=dirpath.name, is_dir=True, children=[])

        try:
            entries = sorted(dirpath.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return VaultTree(path=dirpath, name=dirpath.name, is_dir=True, children=[])

        for entry in entries:
            if should_skip(entry.name):
                continue
            if entry.is_dir():
                count = sum(1 for _ in entry.rglob("*.md") if is_md(_))
                if count == 0:
                    continue
                children.append(VaultTree(
                    path=entry, name=entry.name, is_dir=True,
                    note_count=count, children=_build(entry, depth + 1).children,
                ))
            elif is_md(entry):
                mtime = datetime.datetime.fromtimestamp(entry.stat().st_mtime).strftime("%m-%d")
                children.append(VaultTree(
                    path=entry, name=entry.stem, is_dir=False, mtime_short=mtime,
                ))

        return VaultTree(path=dirpath, name=dirpath.name, is_dir=True,
                         note_count=len([c for c in children if not c.is_dir]),
                         children=children)

    return _build(vault, 0)
