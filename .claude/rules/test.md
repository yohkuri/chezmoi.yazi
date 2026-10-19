---
paths:
  - "test/**"
---

This is the test harness. Before changing it, read
`.agents/skills/verify-chezmoi-yazi/SKILL.md`: its table lists the files each
suite loads, and a change has to pass every suite that loads the file.
`test/support.py`, `test/action_cases.py` and `test/screen.py` reach the
runtime, E2E and guide suites alike, and the guide suite,
`test/manual_runtime.py`, is not in README. It also covers how a
terminal-driven check waits instead of sleeping, the names a fixture plugin
must declare in `test/.luarc.json`, and the cleanup guards that keep a test
inside its own temporary directory.

Running a suite needs nothing from the skill. README's Development section has
the commands; `test/manual_runtime.py` runs the same way, from the repository
root with no arguments.
