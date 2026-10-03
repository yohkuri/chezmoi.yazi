# Validation

Validated locally on 2026-09-20 with Yazi 26.9.1, chezmoi 2.72.2, macOS,
Lua 5.5.1, uv 0.11.19, Python 3.14.7, and tmux. These are tested versions, not a
compatibility claim for every newer/older release or platform.

## Manual fixture

See the [guided manual acceptance walk](../test/MANUAL.md). `test/manual.py`
opens one foreground Yazi with a bottom guide and `W` controls. Preparation,
verdicts, retries, diagnostics, saving and cleanup are available in that session.
Each case/retry gets fresh chezmoi paths; steps within a case share state.

On 2026-10-03, all 24 case setups and step preparations were exercised locally
with Yazi 26.9.1 and chezmoi 2.73.0 on macOS. `test/manual_runtime.py` verified
the real guide and file rows, unanswered-verdict gating, fresh retries,
hidden/compact/full layouts, actual refresh, visual unset preservation,
theme/flavor reload with unchanged epoch, the disposable terminal editor,
encrypted Add, extra-tab disposal, complete long-target selection, source
ancestor rejection, foreground diagnostics, and an in-Yazi exit choice.
A foreground launcher round trip also archived results and removed its owned
fixtures after Yazi exited. The manual launcher itself creates no tmux server;
its automated integration checks use a private socket.

`test/check.py` and the complete `test/runtime.py` passed. An initial runtime
attempt timed out waiting for the resize-restart notification; the unchanged
scenario passed on rerun. This is a timing-sensitive terminal assertion, not
an established product regression.

These automated checks do not constitute human visual acceptance of every
case, font, color, or terminal. The guided launcher with git.yazi, actual editor
integration, and Linux manual acceptance remain unverified. Earlier direct
launcher evidence (2026-09-20) concerns the replaced checklist workflow.

## Automated checks

```sh
npm ci --ignore-scripts
npm run setup:types
test/check.py
test/runtime.py
test/manual_runtime.py
test/e2e.py
test/e2e.py --smoke
# Optional, using an existing git.yazi checkout:
test/runtime.py --git-plugin /absolute/path/to/git.yazi
test/e2e.py --git-plugin /absolute/path/to/git.yazi
```

The pure status suite passes 51 assertions covering path boundaries, NUL framing,
XY preservation, malformed
or out-of-scope status rejection, bounded recovery, resolved differences,
own/descendant independence, summary disabling, and exceptional filenames.
The action suite adds 51 assertions for supported flags, invalid selections,
recursive target reduction, confirmation policy, literal path arguments,
shared context, and matching preview/apply scope.

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
process exit state, plus fixture file effects for command actions. Its complete
local run covers visible status and directory
summaries, manual refresh, directory and tab navigation, template failure and
recovery, theme/flavor reload, wide-sign alignment, and RGB output. The
optional git.yazi scenario verifies both linemodes on the same row and their
order. `--smoke` runs the initial status/refresh scenario and the basic command
scenario used by CI; the full suite also runs the command-edge and
confirmation-pages scenarios.

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
as artifacts. It does not run the full runtime or E2E suites. On 2026-09-20,
both required jobs completed successfully for pull request #1: `checks` and
`E2E smoke`. The latter ran the rendered status and refresh scenario on the
pinned Ubuntu 24.04, Yazi 26.9.1, and chezmoi 2.72.2 environment.

## Command action validation

The command extension was tested on macOS with the baseline versions above.
`test/runtime.py` passed the existing status/rendering suite and the new command,
command-edge, and operation-coordination scenarios. The terminal-driven
command cases are also part of `test/e2e.py`, with the actual chezmoi executable
and no probe or command wrapper in E2E mode.
The full six-scenario E2E run passed; the basic command scenario was rerun after
strengthening exact current-pane status assertions. The direct manual launcher
also opened the new `C` menu and returned to the shell while retaining its fixture.

Measured coverage includes:

- Add/re-add through direct bindings and the menu; forget keeps destination
  files and destroy deletes both entries. Current-pane status and row removal
  are checked after these actions and after apply.
- Diff before apply, refused and accepted apply, native conflict prompts,
  quit without overwriting, and failed template evaluation stopping before apply.
  In this runtime, quitting a native conflict prompt can exit with code zero;
  the notification therefore reports command completion, not changed-file counts.
- Multiple selections, paginated confirmation, selections in another directory,
  known inapplicable mixed targets, and rejection of directory edit.
- Literal spaces, Japanese, quotes, backslashes, CR/LF, leading dashes, and
  shell-looking filenames; recursive and nonrecursive directory add; an orphan
  symlink whose outside referent is not followed or created.
- Template add and re-add skipping; age-encrypted add and transparent
  edit/re-encryption; terminal editor input, Ctrl-C, partial editor failure,
  edit-and-apply success, and cancellation preserving the source edit.
- Standalone diff honoring `[diff].exclude=["scripts"]`, while the apply preview
  includes the script that apply actually runs. Missing descendants are restored.
- An obsolete status query draining before an action; no concurrent mutation
  or refresh subprocess while the action lock is held; target snapshots surviving
  hover movement during menu input; resumption of status acquisition afterward.

On 2026-09-22, an isolated chezmoi 2.72.2 reproduction showed that
`destroy --recursive=false` on a directory still deletes the directory and
its descendants, including an unmanaged child. The plugin now rejects this
combination before confirmation or mutation, including mixed selections; the
file-target form remains available. Three action-policy assertions cover this
boundary. The full `test/runtime.py` suite and wrapper-free
`test/e2e.py --case command-edges` passed with the directory and its child
intact after rejection. `test/check.py` also passed with 51 core and 54 action
assertions and 11 Python tests after the cleanup regression was added.

The fixture's chezmoi config now lives at `config/chezmoi.toml`. Keeping it at
the fixture root caused chezmoi add to protect that whole directory, including
the disposable destination. Interactive instrumentation inherits the terminal
and does not impose the status wrapper's timeout. Tests never use `--force`.

These checks use a disposable editor program and public age test identity.
They do not validate every real editor, GUI editor waiting convention, pager,
interactive secret provider, arbitrary hook, or terminal size. On 2026-09-22,
the basic status-refresh and command scenarios passed in a push-triggered
Ubuntu CI run. A parallel PR run passed both scenarios but failed during
fixture cleanup when a terminating child wrote into the directory being
removed (`ENOTEMPTY`). Cleanup now retries only this bounded race, with a
dedicated regression test. The extended command-edge and operation-coordination
scenarios have not been run on Linux.

### Confirmation and edit regressions

On 2026-09-23, the fixes were checked on macOS with Yazi 26.9.1 and chezmoi
2.72.2. `test/check.py` passed with 51 core assertions, 55 action assertions,
and 11 Python tests. The full `test/runtime.py` suite passed, including action
coordination and confirmation pagination. Wrapper-free E2E runs passed for
`command-edges` and `confirmation-pages`:

- With both `edit.apply=true` and `edit.watch=true`, plain encrypted edit
  leaves the destination untouched. Edit-and-apply also leaves it untouched
  before the diff and after refusing apply; accepted apply still works.
- Six selected targets include long Unicode/control-character filenames and
  a deeply nested path spanning pages. The test reconstructs every complete
  escaped path from visible confirmation rows at 140x40 and 80x18 terminal
  sizes, then cancels the final page and checks that all files remain.
- Resizing during confirmation restarts review at page one. A 40x12 terminal
  produces a current pane below the minimum size and rejects the operation.

These regression scenarios have not been run on Linux or other Yazi versions.

### Cleanup validation

On 2026-10-03, cleanup changes were checked on macOS with Yazi 26.9.1 and
chezmoi 2.73.0. `test/check.py` passed with 51 core assertions, 59 action
assertions, and 11 Python tests. The same checks passed in a temporary snapshot
combining these changes with main's dependency update, including
markdownlint-cli2 0.23.3.

The full `test/runtime.py` suite passed on rerun. Its initial run passed status,
rendering, command, command-edge, and operation-coordination checks, but timed
out waiting for the resize notification during confirmation pagination. The
unmodified HEAD's instrumented confirmation scenario passed in isolation.
Wrapper-free E2E runs of `command-edges` and `confirmation-pages` also passed.
These results do not identify the cause of the initial notification timeout.

Before/after action preparation matched in 6,000 generated comparisons covering
selection scope, rejection messages, duplicate targets, path boundaries, and
confirmation policy. A single CPU-time measurement preparing 10,000 independent
directories fell from 3.9183 s to 0.0171 s after replacing pairwise directory
coverage scans with ancestor lookups. This excludes CLI work and rendering and
does not predict ordinary interactive latency. No new Linux validation was run.

### Source ancestry and visual selection regressions

On 2026-10-03, both review findings were reproduced on macOS with Yazi 26.9.1
and chezmoi 2.73.0 in disposable fixtures:

- With source at `dest/.local/share/chezmoi` and a managed `.local/bin`, recursive
  destroy of `.local` passed plugin preflight. Accepting the first native prompt
  removed the unrelated source entry `dot_bashrc`, while its destination remained.
  Destroy now rejects any target containing the source directory before
  confirmation or execution, regardless of recursion.
- `v`, `j`, `j`, then add captured only the hovered third file and skipped
  multiple-target confirmation. Actions now emit `escape --visual` before the
  synchronous snapshot, committing select and unset ranges through Yazi's own
  selection handling. The same snapshot is used by direct commands and the menu.

`test/check.py` passed with 51 core assertions, 73 action assertions, and 11
Python tests. The full `test/runtime.py` suite passed, including both new
regression scenarios. The source-ancestor case covers recursive/nonrecursive
destroy, an unmanaged ancestor, mixed selections, intact source/destination
entries, and absence of interactive destroy calls. The visual-selection case
covers three-file confirmation, cancellation, menu dispatch, selection in another
directory, unset mode, and resulting source entries.
Wrapper-free `test/e2e.py --case source-ancestor --case visual-selection` also
passed for both scenarios.

The initial sandboxed E2E attempt lost its private tmux sockets before any key
input. Runtime and focused E2E checks therefore ran outside that sandbox with
isolated config, source, destination, state, cache, and tmux paths. No new Linux
validation was run.

## Development tooling checks

Locally verified on 2026-09-20:

- With mise and its shims absent from `PATH`, direct execution of
  `test/check.py`, `test/runtime.py`, `test/benchmark.py`, and
  `test/manual.py` passed, including manual status and cleanup commands.
  The scripts invoke uv themselves; mise is only an optional tool installer.
- `test/check.py`: Markdown clean, LuaLS clean for plugin and harness,
  StyLua clean, all 51 core and 51 action assertions passing, and ten Python
  harness tests passing. The six screen-parser tests cover exact names, missing
  rows, unmanaged spacing, ANSI/hover decorations, pane boundaries, and cell width;
  the other four cover Lua string encoding, CR/LF preservation, cleanup guards,
  and timeout.
- Commit validation: eight valid/invalid message cases, including length,
  capitalization, body spacing, and a body emoji; three commit-range cases
  using an isolated Git repository, including rejection of an invalid commit.
- ShellCheck for the local check scripts and workflow YAML parsing.
- GitHub-hosted runs installed the fixed Linux LuaLS and StyLua releases and
  completed both the development checks and E2E smoke job.
- The Python real Yazi suite passes with and without git.yazi. It preserves
  the Lua harness scenarios, including child lifetime and generation checks.
- Before the command extension, E2E smoke and the four default scenarios passed
  against the visible Yazi screen, as did the optional git.yazi coexistence
  scenario. A temporary
  copy with the managed sign changed from `C` to `X` made the smoke scenario
  fail on the initial status assertion, confirming that it detects a rendered
  status regression rather than only successful process startup.

The initial project commit range from `main` to the pull request head passed
the local commit validator and the pull request's `checks` job. The isolated
Git histories above remain the negative-case coverage for invalid messages.

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

## Force-push commit validation

On 2026-10-03, PR #3 was rebased onto the dependency-update commit from PR #4.
The push workflow failed commit validation because its pre-rebase `before` SHA
was not present in the fresh checkout. The PR workflow and both E2E smoke jobs
passed for the same head. The push workflow now validates all reachable commits
when the previous head is unavailable, as it already does for a new branch.
Available push bases and PR base/head ranges retain their scoped checks.

An isolated single-branch clone reproduced the missing old SHA. The actual
workflow shell block passed normal-push, missing-base force-push, new-branch,
and PR cases, and rejected an invalid commit with a missing push base. Workflow
YAML parsing and full reachable-history commit validation also passed locally.

## Limits of the evidence

The Ubuntu 24.04 E2E smoke scenario is validated in CI. The full runtime and E2E
suites, manual workflow, unusual terminal configurations, and git.yazi
coexistence remain unverified on Linux. Windows, older versions, interactive
secret providers, and arbitrary external hooks are not validated. Windows is
explicitly rejected by setup. Source-state browsing is outside this release.
The direct-child deadline does not promise grandchild termination or cleanup
when Yazi itself exits. The output cap applies after line reads, so one long
line can allocate more than the cap temporarily.

The pure tests are not substitutes for the Yazi suite. Scrolling through very
large interactive lists, unusual grapheme/font combinations, and every
possible hovered-row theme remain manual acceptance areas. The renderer
deliberately leaves hovered signs unstyled to inherit the selected-row style.
