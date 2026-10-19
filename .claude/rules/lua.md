---
paths:
  - "*.lua"
---

This is plugin Lua. Before reporting a change to it as validated, read
`.agents/skills/verify-chezmoi-yazi/SKILL.md`. Any change here needs
`test/runtime.py` and `test/e2e.py` besides `test/check.py`, `core.lua` and
`actions.lua` included: their unit suites check argv and parsing against
hand-written expectations, not against the real chezmoi. CI also runs the
pure suites under Lua 5.1 and 5.4 and parses these files under both, which a
local `test/check.py` does not.

Root-level `.lua` only. The harness under `test/` has its own rule.
