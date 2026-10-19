---
name: verify-chezmoi-yazi
description: >-
  Which of this plugin's test suites a change needs, what each one cannot
  establish, and how to report a run. Read before validating a change to the
  plugin's Lua or to anything under `test/`, and before writing a validation
  claim into a pull request or `docs/validation.md`. Covers the module-to-suite
  map, the Lua 5.1 and 5.4 checks that only CI runs, the runtime suite's
  instrumentation versus the wrapper-free E2E suite, why an automated guide run
  is not a human acceptance walk, writing terminal-driven checks that wait
  rather than sleep, fixture isolation and cleanup, sandboxed tmux sockets,
  and the form a dated validation entry takes. Not needed to run a single
  command; README's Development section lists them.
---

# Validating a change

## Which suites a change needs

Every change runs `test/check.py`. A change to the plugin's Lua, any
root-level `*.lua`, also runs `test/runtime.py` and `test/e2e.py`, whichever
module it touches:

- `core.lua` and `actions.lua` build the arguments given to chezmoi and parse
  what it prints. Their unit suites compare that against hand-written output
  and expected argv, so a flag the real chezmoi rejects passes them once the
  expectation is edited to match.
- `process.lua` runs every chezmoi call. `test/runtime.py` puts
  `test/command.py` between the plugin and chezmoi, so only `test/e2e.py`
  shows the plugin's own calls reaching chezmoi unchanged.

For a change under `test/`, run every suite that loads the file:

| Suite | Loads from `test/` |
| --- | --- |
| `test/check.py` | `core.lua`, `actions.lua`, `test_*.py` and what they import: `screen.py`, `support.py`, `manual_backend.py`, `manual_cases.py` |
| `test/runtime.py` | `support.py`, `action_cases.py`, `screen.py`, `editor.py`, `command.py`, `probe.lua`, `runner.lua`, `child.py` |
| `test/e2e.py` | `support.py`, `action_cases.py`, `screen.py`, `editor.py` |
| `test/manual_runtime.py` | `support.py`, `action_cases.py`, `screen.py`, `editor.py`, `command.py`, `probe.lua`, `manual.py`, `manual_backend.py`, `manual_cases.py`, `manual.lua`, `manual-theme.toml` |
| `test/benchmark.py` | `support.py` |

A suite's own file counts as loaded by it. `support.py`, `action_cases.py`
and `screen.py` reach three suites each, and each suite reads a different kind
of evidence, so one passing says nothing for the others. A change to docs, CI
or tooling alone needs nothing beyond `test/check.py`.

`test/manual_runtime.py` is the guide's own suite. README does not list it; it
runs like the others, from the repository root with no arguments.

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
  non-interactive ones a 10-second timeout. A pass shows the plugin's records
  and rendering agree; it does not show the same behavior without the wrapper.
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

- Every fixture is a `chezmoi-yazi-test-*` directory under the system temp
  directory with its own config, source, destination, state, cache and tmux
  socket. Do not point a test at `~/.config/yazi`, the user's chezmoi source,
  or the default tmux server.
- Two guards limit deletion. `Runtime.close` removes only the directory it
  created, and only while that is a real directory named
  `chezmoi-yazi-test-*`. `support.owned`, which the guide calls before it
  opens, changes or removes a saved fixture, also requires the `manual.json`
  marker naming this checkout. Keep both when changing cleanup; remove only
  what a test created.
- `KEEP_FIXTURE=1` (runtime) and `--keep` (E2E) leave the fixture behind and
  print its path. Report the path; do not delete retained fixtures from earlier
  runs that you did not start.
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
