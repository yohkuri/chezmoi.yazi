# Validation

Validated locally on 2026-09-20 with Yazi 26.9.1, chezmoi 2.72.2, macOS,
Lua 5.5.1, uv 0.11.19, Python 3.14.7, and tmux. These are tested versions, not a
compatibility claim for every newer/older release or platform.

## Manual fixture

See the [manual acceptance checklist](../test/MANUAL.md) for a persistent
fixture with expected displays, refresh and failure scenarios, theme changes,
and ownership-checked cleanup. `test/manual.py` creates the initial state;
it does not reuse the automated suite's final mutated state.

On 2026-09-20, the direct manual launcher was checked in an isolated terminal:
Yazi opened without an attach command, rendered `CMM`, and produced a matching
probe record. Quitting retained the fixture; reopening inside tmux, status,
and ownership-checked cleanup also passed. The launcher creates no tmux server.
The earlier detached fixture was checked with git.yazi on 2026-09-19; the new
direct launcher has not been separately checked with git.yazi enabled.
These checks do not constitute a human visual pass of every checklist step.

## Automated checks

```sh
npm ci --ignore-scripts
npm run setup:types
test/check.py
test/runtime.py
test/e2e.py
test/e2e.py --smoke
# Optional, using an existing git.yazi checkout:
test/runtime.py --git-plugin /absolute/path/to/git.yazi
test/e2e.py --git-plugin /absolute/path/to/git.yazi
```

The pure suite passes 51 assertions covering path boundaries, NUL framing,
XY preservation, malformed
or out-of-scope status rejection, bounded recovery, resolved differences,
own/descendant independence, summary disabling, and exceptional filenames.

The real runtime suite uses a separate Yazi configuration and a private tmux
socket. It inspects plugin state and actual terminal rendering. It covers:

- Setup/fetcher state sharing; managed, unmanaged, clean, `" M"`, `MM`, and `" D"`.
- Missing descendant summaries, `exact_` removals, `.chezmoiremove`, ignores,
  symlinks, and pending scripts (which remain unexecuted).
- Full template evaluation; age-encrypted status, missing identity, recovery.
- Spaces, Japanese text, quotes, backslashes, CR/LF, and leading-dash names.
  Both recursive batches and the nonrecursive CR/LF fallback are exercised.
- Failed templates, independent-file recovery, `C!!`, and partial summaries.
- Manual refresh, directory revisit, tab switching, externally added/forgotten
  entries, failed membership, and recovery.
- Manual refresh during an in-flight older generation; no stale publication.
- Quiescent-view process counts with no periodic polling.
- Silent children, early stdout closure, unfinished output, stderr pressure,
  timeout duration, and confirmation that the direct child has exited.
- Flavor fallback, theme override and hot reload, wide signs, RGB styles.
- Optional git.yazi coexistence and order (git before chezmoi).

The black-box E2E suite does not read the probe, plugin records, or command
history. Each scenario starts a fresh Yazi and asserts on current-pane rows and
process exit state. Its complete local run covers visible status and directory
summaries, manual refresh, directory and tab navigation, template failure and
recovery, theme/flavor reload, wide-sign alignment, and RGB output. The
optional git.yazi scenario verifies both linemodes on the same row and their
order. `--smoke` runs only the initial status and refresh path used by CI.

Test diagnostics live below the isolated state directory so they do not
themselves change files in Yazi's current or parent list. Cleanup affects only
the test-created temporary directory and its private tmux server. No user
configuration is installed, no real dotfiles are applied, and no user Git
history is changed. The public age-manual key in the fixture protects only
disposable test data.

The CI workflow runs the same Markdown, LuaLS, StyLua, and pure test checks
as `test/check.py`, including Python syntax and harness unit tests. It
additionally runs the pure suite and syntax checks on Lua 5.1 and 5.4, and
validates commit messages with commitlint and the ASCII check. A separate
Ubuntu 24.04 job downloads SHA-256-pinned Yazi 26.9.1 and chezmoi 2.72.2
binaries and runs `test/e2e.py --smoke`; failure captures and logs are uploaded
as artifacts. It does not run the full runtime or E2E suites. CI execution
itself has not been observed; the repository has not been pushed.

## Development tooling checks

Locally verified on 2026-09-20:

- With mise and its shims absent from `PATH`, direct execution of
  `test/check.py`, `test/runtime.py`, `test/benchmark.py`, and
  `test/manual.py` passed, including manual status and cleanup commands.
  The scripts invoke uv themselves; mise is only an optional tool installer.
- `test/check.py`: Markdown clean, LuaLS clean for plugin and harness,
  StyLua clean, all 51 core assertions passing, and ten Python harness tests
  passing. The six screen-parser tests cover exact names, missing rows,
  unmanaged spacing, ANSI/hover decorations, pane boundaries, and cell width;
  the other four cover Lua string encoding, CR/LF preservation, cleanup guards,
  and timeout.
- Commit validation: eight valid/invalid message cases, including length,
  capitalization, body spacing, and a body emoji; three commit-range cases
  using an isolated Git repository, including rejection of an invalid commit.
- ShellCheck for the local check scripts and workflow YAML parsing.
- Fixed Linux LuaLS and StyLua release URLs are reachable; this does not
  establish execution on a GitHub-hosted runner.
- The Python real Yazi suite passes with and without git.yazi. It preserves
  the Lua harness scenarios, including child lifetime and generation checks.
- The E2E smoke and all four default scenarios pass against the visible Yazi
  screen. The optional git.yazi coexistence scenario also passes. A temporary
  copy with the managed sign changed from `C` to `X` made the smoke scenario
  fail on the initial status assertion, confirming that it detects a rendered
  status regression rather than only successful process startup.

The empty working repository has no commit range to lint. Commit validation
above used disposable fixture history; no project commit was created.

## Acquisition measurement

```sh
test/benchmark.py
```

This creates a synthetic managed `.config` directory with missing ordinary
files. It times the actual three CLI operations for a
single recursive acquisition scope: destination discovery, managed index,
and status. Sample local results:

| Managed files | Subprocesses | Total CLI time | Combined managed/status bytes |
| --- | --- | --- | --- |
| 100 | 3 | 0.033 s | 21,997 |
| 5,000 | 3 | 0.153 s | 1,095,097 |

These are single-run Python harness measurements, excluding fixture creation, Lua
reduction, rendering, encryption, external resources, and failed-query
recovery. They do not predict real dotfile latency. Ordinary recursive roots
batch well; CR/LF targets require extra queries. Fetcher bursts can produce
multiple acquisition passes. The default 2-second reuse, 8 extra recovery
queries, and 10-second subprocess timeout are configurable operating limits,
not measured optimal settings.

## Limits of the evidence

Linux, Windows, older versions, interactive secret providers, and arbitrary
external hooks are not validated. Windows is explicitly rejected by setup.
Source-state browsing is outside this release. The direct-child deadline
does not promise grandchild termination or cleanup when Yazi itself exits.
The output cap applies after line reads, so one long line can allocate more
than the cap temporarily.

The pure tests are not substitutes for the Yazi suite. Scrolling through very
large interactive lists, unusual grapheme/font combinations, and every
possible hovered-row theme remain manual acceptance areas. The renderer
deliberately leaves hovered signs unstyled to inherit the selected-row style.
