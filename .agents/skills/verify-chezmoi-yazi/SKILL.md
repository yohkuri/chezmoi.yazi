---
name: verify-chezmoi-yazi
description: >-
  Which test suites a change to this plugin's Lua or to `test/` needs, what
  each suite cannot establish, and how to report a run in a pull request or
  `docs/validation.md`, and how to write a terminal-driven check and its
  cleanup. Read before changing the harness, validating a change or writing a
  validation claim; not needed just to run a command, and not for what the
  plugin's Lua must keep true, which `implement-chezmoi-yazi` points to.
---

# Validating a change

## Which suites a change needs

Every change runs `test/check.py`. Then, by what changed:

- **Plugin Lua** (root `*.lua`): `test/runtime.py`, `test/e2e.py` and
  `test/manual_runtime.py`, whichever module it is; the guide drives the
  plugin's own prompts too. `core.lua` and `actions.lua` build chezmoi's
  arguments and parse its output, and their unit suites check that only
  against hand-written expectations, never the real chezmoi.
- **`test/core.lua`, `test/actions.lua`, `test/.luarc.json`, `test/test_*.py`**:
  nothing more locally; CI also runs the two Lua suites under 5.1 and 5.4.
- **`test/manual.py`, `test/manual_*`, `test/manual.lua`,
  `test/manual-theme.toml`**: `test/manual_runtime.py`.
- **`test/benchmark.py`**: `test/benchmark.py`.
- **Any other file under `test/`**: `test/runtime.py`, `test/e2e.py` and
  `test/manual_runtime.py`, plus `test/benchmark.py` for `test/support.py`.
  Most harness files are shared by two or three of these suites, and each
  reads a different kind of evidence, so one passing says nothing for the
  others.
- **Docs (`test/MANUAL.md` included), CI or tooling (`test/check.py`
  included) alone**: nothing more.

## What each suite cannot establish

- **`test/check.py`** never starts Yazi. It also does not run what CI adds:
  both pure suites under `lua5.1` and `lua5.4`, and `luac -p` under 5.1, 5.4
  and 5.5 over the `*.lua` files in the root, `test/` and `scripts/` (not
  `types/`). So Lua 5.5-only syntax in those files, and a pure-suite call such
  as `table.unpack` that an older Lua lacks, fail in CI after passing locally,
  unless you install `lua5.1` and `lua5.4` and run the same commands from
  `.github/workflows/check.yml`.
- **`test/runtime.py`** reads plugin state through `test/probe.lua` and runs
  chezmoi through `test/command.py`, which records every call and gives
  non-interactive ones a 10-second timeout; when a fixture ends without an
  error, `support.check_call` checks each recorded call. A pass shows the
  plugin's records and rendering agree; it does not show the same behavior
  without the wrapper.
- **`test/e2e.py`** sees only the screen, process exit and fixture files. It
  cannot say why a row is wrong, and it has no view of process counts,
  generations or the action lock; those are runtime-only assertions.
- **`test/manual_runtime.py`** presses the guide's keys in a private tmux. It
  is an automated execution check of the guide, never a human acceptance walk,
  whatever verdicts it records.
- **`test/benchmark.py`** times three CLI calls in a synthetic tree. It does
  not predict latency in a real dotfiles repository.
- **CI** runs `test/e2e.py --smoke` (status-refresh and commands) on Ubuntu
  24.04 with pinned Yazi and chezmoi. The full runtime, E2E and guide suites
  run only where someone runs them by hand, which so far means macOS.

Nothing here establishes Linux beyond the smoke run, other Yazi versions,
git.yazi in the guided walk, a real editor, or a person's judgment of
readability. Say so rather than letting a green run imply it.

## Writing a terminal-driven check

- Wait on the screen or the probe with `wait_screen`, `wait` or `refresh`,
  not on a sleep. `docs/validation.md` records several added checks that sent
  keys too early and passed only after an explicit wait replaced the settle.
- Wait for the previous action to finish before the next key: a recorded
  verdict, a released action lock, a prepared fixture. Keys sent early answer
  the wrong prompt.
- Send Escape on its own and let it settle before the next key, as
  `test/manual_runtime.py` does. Followed at once by a digit, it decoded as
  Alt+digit.
- Text wraps at the terminal width, and the harness resizes to as narrow as
  40 columns. Assert on a phrase that survives wrapping at the narrowest size
  the check runs at, or on `screen.row` for file rows.
- A fixture plugin under `test/` gets values as `local` lines prepended by
  `Runtime.plugin`. A new name needs an entry in `diagnostics.globals` of
  `test/.luarc.json`, and an `--- @sync entry` annotation must stay the file's
  first line, where `Runtime.plugin` looks for it.

## Isolation and cleanup

- Two guards limit deletion. `Runtime.close` removes only the directory it
  created, and only while that is a real directory named
  `chezmoi-yazi-test-*`. `support.owned`, which the guide calls before it
  opens, changes or removes a saved fixture, also requires the `manual.json`
  marker naming this checkout. Keep both when changing cleanup; remove only
  what a test created.
- Report the path a kept fixture prints (`KEEP_FIXTURE=1`, `--keep`); do not
  delete fixtures kept by runs you did not start.
- Tests never pass `--force` to chezmoi. A prompt in a test is either expected
  and answered by the test, or a bug.
- A restricted agent sandbox has lost the private tmux sockets before any key
  input. If a Yazi-driven suite fails that early, rerun the same command
  outside the sandbox and say that you did.

## Reporting a run

- Name each command that ran and its result. For a Yazi-driven suite, add the
  OS and the Yazi and chezmoi versions (`yazi -V`, `chezmoi --version`).
- Quote the counts `test/check.py` prints: core assertions, action policy
  assertions and Python tests. A count that changed is part of the change.
- Disclose reruns. A failure that passed unchanged on rerun is reported as a
  timing-sensitive failure, not dropped. The confirmation-pagination resize
  notification has timed out this way before; a new flaky assertion is a
  finding, not noise.
- Distinguish an automated guide run from a human walk, and an injected
  failure from one that happened. Never record a guided-session verdict on the
  user's behalf.
- A change that alters what was validated adds a dated entry to
  `docs/validation.md` in the same pull request: what ran, the versions, the
  counts, what failed first and why, and what stays unverified.
