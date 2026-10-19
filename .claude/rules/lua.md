---
paths:
  - "*.lua"
---

This is plugin Lua. Before reporting a change to it as validated, read
`.agents/skills/verify-chezmoi-yazi/SKILL.md`: `test/check.py` reaches only
`core.lua` and `actions.lua` without Yazi, so the other modules need
`test/runtime.py` or `test/e2e.py`, and CI also parses every Lua file under
Lua 5.1 and 5.4, which a local `test/check.py` does not.

Root-level `.lua` only. The harness under `test/` has its own rule.
