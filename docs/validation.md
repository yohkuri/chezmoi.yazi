# Validation

Validated locally on 2026-09-20 with Yazi 26.9.1, chezmoi 2.72.2, macOS,
Lua 5.5.1, uv 0.11.19, Python 3.14.7, and tmux. These are tested versions, not a
compatibility claim for every newer/older release or platform.

## Manual fixture

See the [guided manual acceptance walk](../test/MANUAL.md). `test/manual.py`
opens one foreground Yazi with a bottom guide, single-key `P` acceptance,
`S` skip/advance and `W` controls. Preparation,
verdicts, retries, diagnostics, saving and cleanup are available in that session.
Each case/retry gets fresh chezmoi paths; steps within a case share state.

The current walk has 12 cases and 34 steps focused on human UI acceptance:
readability, command effects/targets/options, menu and native prompts, diff and
approval stages, cancellation, interruption, rejection messages and terminal
return. File/state outcomes are checked automatically. Refresh/cache behavior,
membership discovery, navigation/tabs and visual-unset bookkeeping remain in
automated runtime coverage. The dated 24-case evidence below describes the
preceding catalog, not the current case numbers.

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

On 2026-10-04, four guided-session state defects were corrected. Checking a
skipped step preserves SKIP unless an automatic check fails; leaving a case
preserves NOT RUN and ERROR instead of promoting them to PASS. The git plugin
path is resolved before persistence, error markers identify their originating
attempt/step, and a fresh case clears the completed-walk flag. Seven added
harness regressions passed, including malformed/missing error-token fallback
and archival after changing cases. Error markers were injected for attribution
checks; this does not establish behavior under an actual backend timeout.

`test/manual_runtime.py` passed with Yazi 26.9.1 and chezmoi 2.73.0 on macOS.
Real `W/s`, `W/d`, and `W/n` interactions preserved a skipped case's saved
result; restart and jump after completion restored the case title. Separate
backend CLI processes exercised relative git plugin paths across working
directories for both restart and jump. That path test used a disposable stub
plugin and did not validate actual git.yazi rendering or coexistence.

`test/check.py` passed with 51 core assertions, 73 action assertions, and 29
Python tests; the complete `test/runtime.py` also passed. The first added
terminal scenario sent the next control before SKIP was recorded and timed
out. It now waits for the recorded verdict, and the guided suite passed on rerun.

On 2026-10-11, both follow-up review findings were reproduced and corrected.
Backend exceptions now update the case aggregate as well as the step. Saved
case results are recomputed from the latest attempt for each case, so an older
attempt's error cannot overwrite a successful retry. The originating error,
marker, and failed fixtures remain available for diagnosis.

Two added regressions cover exception responses, persisted and archived
aggregates, and old errors after retrying and changing cases. They preserve
the latest PASS, SKIP, NOT RUN, FAIL, or ERROR. `test/check.py` passed with 51
core assertions, 73 action assertions, and 31 Python tests. An isolated real
chezmoi encrypted-file corruption produced a decryption exception: the step,
case, and archive all recorded ERROR after the fix. A fresh encrypted Add
retry then archived PASS while preserving the older error marker. The marker
was injected; an actual backend timeout was not induced.

The complete `test/manual_runtime.py` and `test/runtime.py` passed on macOS
with Yazi 26.9.1 and chezmoi 2.73.0, using isolated fixtures and private tmux
sockets outside the restricted sandbox. No new Linux validation was run.

Follow-up quality cleanup on the same date centralized result aggregation at
save/archive boundaries, reused the shared text reader, and simplified fixture
and verdict code. Guide requests now copy full status snapshots only for
operations that inspect them; acquisition waits use lightweight progress data.
Forbidden-command checks seek to the relevant log offset and stream records,
while diagnostics select the same first 80 paths without sorting the full tree.

A focused comparison against the preceding commit confirmed identical results
for multibyte log records with byte offsets, the first 80 sorted paths, and all
16 combinations of automatic and visual verdicts. Existing exception/retry
regressions and isolated encrypted-file checks also passed. These checks do not
measure startup latency or memory savings.

After cleanup, `test/check.py` passed all 31 Python tests, 51 core assertions,
and 73 action assertions; the complete `test/manual_runtime.py` and
`test/runtime.py` passed on the same macOS/Yazi/chezmoi versions.

A further correctness review on 2026-10-11 reproduced three guide defects.
Ctrl-C in the fixture editor also interrupted the waiting launcher; stale
backend requests changed the current case to ERROR; a second guide error
overwrote the first marker. The launcher now catches SIGINT while waiting,
allowing foreground children to handle it, and restores its handler afterward.
Stale requests return the current view and a message without changing saved
progress. Guide failures append to `manual-errors.jsonl`; the next valid request
or finalization imports new entries once, records their originating steps, and
retains the complete history. Legacy single markers remain supported.

Three added regressions passed, covering stale CLI responses without persisted
changes, multiple error origins and archived history, and successful rechecks
without old errors being reapplied. An actual backend CLI process also returned
the unchanged PASS result for a stale token. A private-tmux test launched the
executable `test/manual.py`, interrupted its fixture editor twice, continued
guide controls, recorded PASS for unchanged files, and verified archive/cleanup.
Two injected diagnostic-command failures in real Yazi produced separate Lua
journal entries and ERROR for both originating cases in the saved report.
This tests the error path, not an actual backend timeout.

After these fixes, `test/check.py` passed 34 Python tests, 51 core assertions,
and 73 action assertions. The complete `test/manual_runtime.py` and
`test/runtime.py` passed on macOS with Yazi 26.9.1, chezmoi 2.73.0, and
Python 3.14.8. Initial added terminal checks advanced before action completion
or journal append; their waits were corrected before the passing runs.

Quality cleanup of that follow-up commit shared the terminal guide controls
and case chooser between the guide suite and foreground launcher, preserving
their existing key order and settle intervals. The multiple-error regression
now reuses one loaded state for its assertion and subsequent updates.
`test/check.py` again passed 34 Python tests, 51 core assertions, and 73 action
assertions. The complete `test/manual_runtime.py` and `test/runtime.py` also
passed after this cleanup on the same macOS/Yazi/chezmoi/Python versions.

On 2026-10-16, a human walk of the preceding guide recorded 22 PASS and two
SKIP cases, with no final FAIL or ERROR. Manual refresh was skipped because
automatic acquisition updated the signs before `R`; git coexistence was skipped
because no git plugin was supplied. The walk exposed unclear observations,
unnecessary navigation/selection keys, repeated verdict/next menus, clipped
instructions, missing command visibility, and stale instructions at completion.

The revised English guide uses `P` to record visual PASS, check files/state and
advance only on success. Failed checks stay on the current step, rapid repeated
presses are ignored, and stale requests cannot answer the next step. `N`, `B`
and `S` overrides were removed in favor of normal navigation and Escape. Wrapped
instructions include concrete expectations and intended command stages; completed
screens show case results. The manual-refresh case holds its cache for 24 hours
and checks that a new acquisition occurred. Interactive execution displays actual
argv, and fixture reports retain interactive command argv and exit codes.

Five new unit regressions cover acceptance/advancement, failed-check gating,
persistence before preparation errors, forced-refresh evidence and completed
results. Archive checks also verify that command history survives cleanup.
`test/check.py` passed 39 Python tests, 51 core and 73 action assertions. The
complete `test/runtime.py` and `test/manual_runtime.py` passed with isolated
fixtures and private tmux sockets on macOS, Yazi 26.9.1 and chezmoi 2.73.1.
The guide suite checked repeated `P`, wrapping at 80 columns, failed acceptance
before `R`, real refresh, actual argv/history, cancelled apply, standard Escape,
completion, and repeated foreground editor interruption with archive/cleanup.

Initial added terminal assertions needed to await fixture preparation, account
for wrapped text, and separate Escape from the following digit so it was not
decoded as Alt+digit. Those test issues were corrected before the passing run.
The revised controls and instructions have not yet had another human acceptance
walk, and no new Linux, personal-editor or actual git coexistence run was done.

Follow-up cleanup on 2026-10-16 colocated command descriptions and epoch/cache
policies with case/step definitions. Baseline snapshots now run only for the four
steps that inspect epochs. Layout and redraw share wrapped guide lines, and
acceptance and Next share advancement while retaining the PASS save before
preparation. Prepared attempts are published only after preparation succeeds.
Existing refresh, command-finish, current-attempt and owned-cleanup helpers are
reused; empty preparation avoids context reconstruction. Result aggregation
examines only the latest attempt per case, while retaining all historical errors.
Saved-state fields, attempt metadata and case-wide forbidden-command checks remain.

A comparison of all 24 cases and 49 steps preserved the existing instructions,
expectations, preparation and command descriptions. An added regression verifies
that failed case preparation preserves the previous attempt. `test/check.py`
passed 40 Python tests, 51 core and 73 action assertions; the complete
`test/manual_runtime.py` and `test/runtime.py` passed. The first runtime attempt
timed out waiting for the existing resize-restart notification; the unchanged
suite passed on rerun. These checks used isolated macOS/Yazi 26.9.1/chezmoi 2.73.1
fixtures and do not measure latency or replace human acceptance of the revised UI.

A subsequent review reproduced a saved-session regression: reopening Manual
refresh at step 2 or 3 cleared its epoch baseline without collecting a new one,
so recording PASS still failed after `R`. Guide startup now captures the new
process baseline before accepting actions. Added real-terminal regressions run
`test/manual.py open PATH` at both saved steps, reject PASS before `R`, and verify
that `R` followed by `P` records PASS and advances. Both resumed-step checks passed.
`test/check.py` (40 Python tests, 51 core and 73 action assertions) and the complete
`test/manual_runtime.py` and `test/runtime.py` also passed after the fix.

A later independent review exposed an exception-handling gap: `transition()`
saved PASS before preparation, but the CLI error handler overwrote that verdict
with ERROR if preparing the next step or case failed. CLI-path regressions
reproduced the overwrite for acceptance, Next, Jump and Restart, including
unanswered steps. Preparation failures now retain the saved position and verdicts,
record the intended case/step and operation separately, appear in `W/d`, and
retain fixtures after later successful retries. Check exceptions still mark
their current step ERROR, and preparation history does not consume guide-error
journal entries. `test/check.py` passed 42 Python tests, 51 core and 73 action
assertions, including archive retention and diagnostic-history checks.
The complete `test/manual_runtime.py` and `test/runtime.py` also passed. The guide
suite injected a real Restart preparation failure and verified unchanged verdicts,
the intended target in the notification, and error history in foreground details.
Its first run sent PASS before a rejected action released its lock; explicit
action-completion waits were added before the successful complete rerun.

The human guide now presents numbered English instructions in execution order,
placing each visible check immediately after its action. Command names are
included with the keys that invoke them, and each existing step ends with one
`P` verdict rather than adding verdicts for individual instructions. The bottom
guide and foreground details share this prose without separate Do, Expect or
Command sections. A comparison of all 24 cases and 49 steps confirmed unchanged
case order, setup, preparation, file/state expectations, epoch policies and cache
settings. `test/check.py` passed 42 Python tests, 51 core and 73 action assertions.
The complete `test/manual_runtime.py` passed, including instruction order at 80
columns, matching prose in foreground details, saved-session resume and cleanup.
The complete `test/runtime.py` also passed with isolated fixtures and private
tmux sockets.

Single-key `S` now records SKIP for the current step and advances without a
reason prompt or file/state checks. `W/s` still accepts an optional reason and
stays on the step. The new binding replaces content search only in the manual
session and is refreshed when reopening retained sessions. `P` and `S` share
the repeat-key guard; completed walks ignore both. A narrow guide uses a shorter
reminder that fits `P`, `S` and `W` at 40 columns.

Three added unit regressions cover SKIP advancement without checks or answering
the following step, persistence across preparation failure, and completion
without PASS. Existing case-preparation checks now include SKIP advancement.
`test/check.py` passed 45 Python tests, 51 core and 73 action assertions.
The complete `test/manual_runtime.py` verified within-case and cross-case SKIP,
mixed/repeated verdict keys, the 40-column reminder, unchanged `W/s` behavior,
completed-walk handling and the new binding when resuming an older keymap.
The complete `test/runtime.py` also passed on macOS with Yazi 26.9.1 and chezmoi
2.73.1. Initial added checks needed a complete fixture and explicit separation
from the repeat-key guard; the terminal sequence also avoids reentering the
case it has just reached and waits for the first verdict before sending repeats.

The manual session now bundles explicit Catppuccin Mocha status-bar and tab
colors in `test/manual-theme.toml`. No personal flavor or network download is
required. The baseline persists across case changes and chezmoi theme overrides;
retained sessions keep their saved baseline. Reports include the palette's source
hash. A regression covers custom/base theme transitions with and without git
context. `test/check.py` passed 46 Python tests, 51 core and 73 action assertions.
The complete `test/manual_runtime.py` injected light and dark terminal reports,
verified Yazi's own appearance detection, and checked rendered RGB colors in
normal, select and unset status modes, plus preservation through Case 8.
The complete `test/runtime.py` also passed on macOS with Yazi 26.9.1 and chezmoi
2.73.1. These captures verify emitted colors, not physical display calibration.

On 2026-10-18, the human walk was consolidated from 24 cases/49 steps to
12 cases/34 steps. Add, Re-add, template/encrypted Add, Forget, Destroy, Diff,
Apply and Edit retain their distinct command UI paths. Multiple-target review
combines direct/menu selection with a target in another directory. Rejection
messages share one fixture whose source is nested below the destination while
retaining the baseline managed files. Template failures and partial summaries
are introduced sequentially to keep each warning observation focused.

The session format now records version 2 and ordered case keys. Opening an
older or reordered catalog is rejected before modifying progress, launching
Yazi or archiving; a regression verifies unchanged saved bytes and retained
fixtures. Existing reports, status queries and explicit cleanup remain usable.
New-catalog sessions still resume their saved steps. Both theme steps were
reopened with a stale epoch from the previous process; the launcher captured
the new baseline and `Y` then `P` advanced successfully.

`test/check.py` passed 47 Python tests, 51 core and 73 action assertions.
The complete `test/manual_runtime.py` and `test/runtime.py` passed on macOS
with Yazi 26.9.1 and chezmoi 2.73.1. Guide checks exercised the consolidated
command flows, native Forget/Destroy approval, file-check failure gating,
cross-directory confirmation, repeated foreground Ctrl-C, archive/cleanup and
resumed theme steps. Existing refresh, navigation and visual-unset scenarios
remain automated. The guide's case numbers/titles were also compared with
the manual table. These are automated execution checks, not a new human walk.

Follow-up cleanup removed the unused Destroy log offset, refresh-only epoch
branch, per-case cache TTL and old guide-response fields. Theme sign expectations
now live beside their steps and use a common comparison. The frontend receives
case results directly and omits full snapshots for Next after a recorded verdict.
CLI tests share their existing invocation helper, P/S timing shares one sender,
and filename expectations reuse the baseline fixture list.

A comparison preserved all 12 cases/34 steps, including instructions,
preparation and file/state/theme expectations. `test/check.py` passed 47 Python
tests, 51 core and 73 action assertions. The complete `test/manual_runtime.py`
and `test/runtime.py` passed on the same macOS/Yazi/chezmoi versions. A trial
cache of wrapped `ui.lines()` objects caused `ui.Text` redraw errors and was
discarded before the passing guide run; wrapping still runs on layout. These
checks do not measure a startup or memory improvement or establish human
visual acceptance.

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
