---
paths:
  - "test/**"
---

This is the test harness. Before changing it, read
`.agents/skills/verify-chezmoi-yazi/SKILL.md`: which suite a change here has
to pass, since `test/action_cases.py` and `test/support.py` feed both the
instrumented runtime suite and the wrapper-free E2E suite, and a guide change
needs `test/manual_runtime.py`, which README does not list. It also covers how
a terminal-driven check waits instead of sleeping, the names a fixture plugin
must declare in `test/.luarc.json`, and the cleanup guards that keep a test
inside its own temporary directory.

Running a suite needs nothing from the skill; the commands are in README's
Development section.
