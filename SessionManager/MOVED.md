# SessionManager moved

The SessionManager repo no longer lives at `~/A/SessionManager/`.
It is now part of Cruft.

**New location:** `~/CRAP/SessionManager/`

The Windmill bridge that used to live inside SessionManager
(`f/sessions/`) is now a sibling of the repo:

  - Library code: `~/CRAP/SessionManager/sessions/`
  - CLI / TUI / hook entrypoints: `~/CRAP/SessionManager/scripts/`
  - Windmill bridge: `~/CRAP/f/sessions/`
  - Windmill sync config: `~/CRAP/wmill.yaml`

This file is a stub left at the old location so anyone (or anything)
that follows a stale path lands here instead of an opaque "no such
directory". Safe to delete once stale references are scrubbed.

Moved on 2026-05-02.
