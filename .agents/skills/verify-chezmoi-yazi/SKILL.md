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

Every change runs `test/check.py`. The rest depends on what moved:

| Changed | Also run |
| --- | --- |
| `core.lua`, `actions.lua` | Nothing more unless the change shows on screen |
| `main.lua`, `render.lua`, `interaction.lua` | `test/runtime.py`, `test/e2e.py` |
| `process.lua` | `test/runtime.py` (its child-process checks live only there) |
| `test/support.py`, `test/action_cases.py` | `test/runtime.py`, `test/e2e.py` |
| `test/screen.py` | `test/e2e.py` |
| `test/manual.py`, `test/manual_*`, `test/manual.lua`, `test/manual-theme.toml` | `test/manual_runtime.py` |
| Docs, CI, tooling only | Nothing more |

`test/core.lua` and `test/actions.lua` load the pure modules with `dofile`,
so those two suites are the only ones that reach `core.lua` and `actions.lua`
without Yazi. Everything else in the plugin is exercised only inside a running
Yazi.

`test/action_cases.py` is shared: `test/runtime.py` drives it through the
instrumented chezmoi wrapper and the probe, `test/e2e.py` through the real
binary with neither. A change there has to pass both, because each suite reads
a different kind of evidence.

`test/manual_runtime.py` is the guide's own suite. README does not list it,
but a change to the guide is not validated without it.

## What each suite cannot establish

- **`test/check.py`** never starts Yazi. It also does not run what CI adds:
  `lua5.1` and `lua5.4` over both pure suites, and `luac -p` under 5.1, 5.4
  and 5.5 over every `*.lua` in the root, `test/` and `scripts/`. Lua 5.5-only
  syntax anywhere fails CI while passing locally, unless you install `lua5.1`
  and `lua5.4` and run the same commands from `.github/workflows/check.yml`.
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
- Text wraps at the terminal width. Assert on a phrase that survives wrapping
  at 80 columns, or on `screen.row` for file rows.
- A fixture plugin under `test/` gets values as `local` lines prepended by
  `Runtime.plugin`. A new name needs an entry in `diagnostics.globals` of
  `test/.luarc.json`, and an `--- @sync entry` annotation must stay the file's
  first line, where `Runtime.plugin` looks for it.

## Isolation and cleanup

- Every fixture is a `chezmoi-yazi-test-*` directory under the system temp
  directory with its own config, source, destination, state, cache and tmux
  socket. Do not point a test at `~/.config/yazi`, the user's chezmoi source,
  or the default tmux server.
- `support.owned` and `Runtime.close` refuse to delete anything that is not a
  marked fixture. Keep those guards when changing cleanup; remove only what a
  test created.
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
