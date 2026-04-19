import re
patterns = [
    re.compile(rb"(?im)^Co-authored-by:\s*.*(?:Claude|Codex|Bots|Manus|Copilot|Dependabot|github-actions).*(?:\r?\n)?"),
    re.compile(rb"(?im)^.*Generated (?:with|by).*(?:Claude|Codex|Bots|Manus|Copilot).*(?:\r?\n)?"),
]
msg = commit.message or b""
for p in patterns:
    msg = re.sub(p, b"", msg)
msg = re.sub(rb"(\r?\n){3,}", b"\n\n", msg).rstrip() + b"\n"
commit.message = msg
