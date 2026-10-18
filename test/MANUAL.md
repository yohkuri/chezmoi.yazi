# Guided manual acceptance

Launch from the repository root in an interactive terminal:

```sh
test/manual.py
```

Yazi opens directly in the same terminal. Follow the bottom guide; press `P`
to record visual PASS, check files/state and advance on success. Press `S` to
record SKIP for the current step and advance without a reason prompt or checks.
Press `W` for other verdicts, controls or full instructions. Fixture edits, failure
injection, checks, retries, results and cleanup are handled from this session.
You do not need another terminal, shell commands after launch, or an external
checklist. The [case list](#cases) gives the number, title and purpose of all
12 cases.

Human acceptance covers what is readable and understandable in your terminal:
status signs and colors, command effects and targets, menus, diff/approval
stages, native prompts, cancellation, interruption, warnings and return to Yazi.
File contents, deletion, encryption, rejected invocations and plugin state are
checked automatically when you press `P`; you do not need to inspect them by hand.
Refresh/cache correctness, membership discovery, tab/navigation state and visual
unset bookkeeping remain automated tests rather than separate human cases.

## Requirements

Have Yazi 26.9.1+, chezmoi and uv on `PATH`. The executable launcher uses the
locked uv environment; no pip packages, Neovim or tmux are needed for this walk.
Keep the checkout and its `.venv` in place until the session ends. A terminal
at least 100 columns wide is convenient; smaller sizes are acceptance cases.
Public UI and instructions are English. Unicode filenames are intentional.
Linux and every font/terminal combination are not established by this guide.

The session uses explicit Catppuccin Mocha colors for the status bar and tabs
in both dark and light terminal appearances. It reads the bundled
`test/manual-theme.toml`, without loading personal configuration or downloading
a flavor. Case 3 changes chezmoi signs and colors while retaining these UI
colors. Start a new session to use this palette; retained sessions keep their
saved baseline theme.

Optionally include an existing, read-only git.yazi checkout at startup:

```sh
test/manual.py --git-plugin /absolute/path/to/git.yazi
```

Without it, case 12 is automatically recorded as `SKIP` with a reason. The
walk can therefore finish after case 11 while still reporting 12 case results.

## Walking a case

Start with case 1 and follow its guide. A heading such as `1/12 ... - step 1/2`
means case 1 of 12, step 1 of that case's two steps. The complete walk has
34 steps; each step contains several numbered instructions.

The guide shows the case and step, followed by numbered English instructions
in execution order. Each action is followed by what to check before the next
action. Command names appear beside the keys that invoke them. Press `P` once
after completing the whole current step; numbered instructions do not add
separate verdicts. File and directory names in instructions are enclosed in
double quotes. Quotes, backslashes and control characters inside names use JSON
escapes, such as `"quote\"name"`, `"back\\slash"` and `"new\nline"`.
Text wraps to the terminal width. If it exceeds the guide height,
the guide directs you to `W`, then `d` for complete instructions and diagnostics
in the same terminal. Enter advances that viewer, `b` then Enter goes back, and
`q` then Enter returns to Yazi. The viewer also lists every case number, title
and current result under `CASES`; continue through its pages to reach that list.

1. Perform the indicated operation using normal Yazi navigation or the fixture
   keys below. The fixture prepares file changes and injected failures when
   you enter the step. Press `R` or `Y` yourself when instructed.
2. Inspect the visible result. Press uppercase `P` (Shift+p) once to record visual
   `PASS`, run the file/state checks, and advance only if every check passes.
   `W`, then `p` does the same. Failed checks retain the current step and explain
   the failure; `W`, then `d` shows details. Rapid repeated `P` presses are ignored
   until there has been a short pause between presses. The same repeat guard
   applies to `S`, including quick switches between `P` and `S`.
3. If you cannot test the current step, press uppercase `S` (Shift+s) to record
   SKIP and advance. This skips only that step, not the whole case, and records
   `Skipped by tester` without asking for a reason or running checks.
   Use `W`, then `f` to record failure or `W`, then `s` to skip with a reason.
   These keep the current step for inspection; `W`, then `n` continues afterward.
   Unanswered observations cannot advance. Automatic checks never supply your
   visual verdict.
4. Use `W`, then `r` to retry the current case from a fresh fixture, or `W`,
   then `j` to enter a case number. Jumping starts the chosen case from its
   first step with a fresh fixture. Previous attempts remain available as evidence.

In case 1, `".config"` is intentionally empty even though its row has `*`:
the source contains changes that have not been applied to the destination.
You inspect the destination in Yazi. This explains the sign; opening the
directory to verify its contents is not a separate human acceptance step.

Each case and retry has a new source, destination, database and command cache.
Steps within a case share those paths. Changing cases clears selection, closes
extra tabs and restores the baseline theme. Opening guide controls preserves
ordinary and visual selections. Guide transitions and actions are serialized;
wait for the current command to return before recording or changing cases.

The wrapped guide uses at most half the terminal height above the ordinary
status bar; short terminals show a one-row key reminder. `W`, then `d` remains
available for full instructions. `W`, then `h` hides/restores the guide. Hidden
mode restores Yazi's normal layout and keeps `W` available. Hide it for
normal-layout resize/small-pane tests.
Modal confirmations appear above the guide.

## Keys

Keys are case-sensitive. These overrides affect only the disposable session.
Uppercase `P` (Shift+p) records a result; lowercase `p` requests Apply.
Uppercase `S` (Shift+s) skips the current step. It replaces Yazi's content
search binding only in this disposable session; lowercase `s` keeps name search.
In the tables, `W` then another key means two consecutive key presses.

### Guide controls

Use these while the Yazi file list is visible. A command, editor or confirmation
may have its own keys; finish or cancel that interaction before using the guide.

| Key | Operation |
| --- | --- |
| `P` or `W` then `p` | Record visual PASS, check files/state, and advance on success |
| `S` | Record SKIP for the current step and advance, without a reason prompt or checks |
| `W` then `f` | Record visual FAIL and optional observation; stay on the step |
| `W` then `s` | Record SKIP and optional reason; stay on the step |
| `W` then `n` | Continue after a recorded verdict or skip, even if checks failed |
| `W` then `r` | Restart the current case from step 1 with a fresh fixture |
| `W` then `j` | Enter a case number to start it with a fresh fixture |
| `W` then `d` | Recheck files/state and open full instructions, case results and diagnostics |
| `W` then `h` | Hide or restore the guide |
| `q` or `W` then `q` | Open the results/exit menu; Escape returns to the walk |

In the details viewer, press Enter to advance a page, or type `b` then Enter
to go back. Type `q` then Enter to return to Yazi. Opening details can update
file/state checks, but never supplies a visual verdict or advances the step.

### Navigation and plugin actions

| Key | Operation |
| --- | --- |
| `j`, `k`, arrows, `h`, `l` | Normal navigation |
| Space | Toggle hovered selection without moving |
| Escape | Standard Yazi selection/mode escape; press again if still selected |
| `v`, `V` | Normal visual select/unset |
| `C` | Real chezmoi action menu |
| `R`, `Y` | Refresh status / reload theme |
| `a`, `r`, `e`, `E` | Add / Re-add / Edit / Edit and apply |
| `d`, `p`, `f`, `x` | Diff / Apply / Forget / Destroy |
| `D` | Destroy with `--recursive=false` |
| `t`, `z` | Add as template / encrypted Add |
| `G`, `H` | New `".config"` tab / tab zero |
| `1`, `2`, `3` | Reveal `"range-a"` / `"menu-a"` / `".config/outside"` |
| `4` | Select all long/deep confirmation targets |
| `5`, `6`, `7`, `8`, `9`, `0` | Reveal `".local"` / `"source"` / `"unmanaged"` / `"clean"` / `".config"` / `".exact"` |
| `T` | Write the internal diagnostic probe |

Move the cursor to a directory and press `l` to enter it; press `h` to return
to its parent. Use Space only when the guide asks for a selection. An action
uses the selected targets when present, otherwise the file under the cursor.

### Status signs

The default chezmoi columns contain a managed sign, two status characters and
a directory summary. Spaces matter; the guide omits trailing spaces when it
names a sign.

| Display | Meaning in the fixture |
| --- | --- |
| `C` with blank status columns | Managed and clean |
| `CMM` | Managed file with a destination edit |
| `C M` | Managed file whose source would change the destination |
| `C D` | Managed destination scheduled for removal |
| Blank columns | Unmanaged or ignored file |
| `*` after a directory's status columns | Changes below that directory, including missing destination entries |
| `C!!` | Managed file whose status query failed |
| `!` in the managed column | Membership query failed |

Directory summaries can also have a partial-result underline. Case 3 changes
the default signs and colors temporarily; its guide gives the expected values.

### Commands and refresh

Commands use real chezmoi and its native prompts, with no forced confirmation.
The guide's command description omits shared fixture context and abbreviates
target paths. Each execution screen starts with `chezmoi <subcommand>`, such as
`chezmoi add` or `chezmoi diff`, for the stage actually running. It also shows the
complete executable and argument vector as JSON, preserving quotes and control
characters. `W`, then `d` lists executed interactive commands and exit codes
separately from background status queries; this history is included in the saved
report. A cancelled or
rejected action may run validation queries, but does not execute the rejected
interactive command. Edit and Apply runs edit, diff, then apply only after approval.
Read output and press Enter when the command asks to return to Yazi. For Apply,
return from the diff first, then answer the plugin confirmation. Destructive
commands can also have a native chezmoi prompt after plugin confirmation.

Edit cases use a disposable terminal editor displaying the current source.
Type the instructed replacement line and Enter to save; Ctrl-C interrupts it.
It requires no personal editor configuration. Encryption uses a public test age
identity inside the fixture; it is never suitable for real secrets.

Press `R` when the warning/recovery guide requests acquisition. These cases
use a short cache, so automatic acquisition may update signs before `R`; this
is acceptable because the human verdict concerns the display and warning.
Intentional failures say which warning and signs to expect; an expected warning
alone does not mean that the test failed. Theme steps use `Y`, which reloads
appearance without refreshing status. Refresh/cache semantics are checked by
the automated runtime suite.

## Cases

These numbers and titles match the current guide and `W` then `j` jump input.
Detailed instructions, preparation and automatic checks live in
[`manual_cases.py`](manual_cases.py). Use `W` then `d` to see the current
session's case results.

| Case | Title | Human UI check |
| --- | --- | --- |
| 1 | Status, names and readability | Distinct signs, special filenames, aligned columns, selection/hover contrast, status bar and narrow layouts |
| 2 | Warnings, error signs and recovery | Template/membership warnings, error signs, partial-result underline and readable recovery |
| 3 | Theme, wide signs and colors | Default/custom/restored colors and wide signs, with readable status-bar colors |
| 4 | Add, Re-add, template and encryption | Direct/menu execution, effects, targets, options, output and return to Yazi |
| 5 | Forget confirmation and cancellation | Keep-destination wording, cancellation, plugin/native approval and return |
| 6 | Destroy confirmation and execution | Delete-source-and-destination warning, plugin/native approval and return |
| 7 | Diff, Apply preview and approval | Readable standalone diff, cancelled Apply, directory/script scope and approved Apply |
| 8 | Edit, Edit and Apply, and interruption | Editor/diff/approval stages, cancellation, Ctrl-C result and return to usable Yazi |
| 9 | Rejected actions and safety messages | Mixed/unmanaged targets, directory Edit, shallow Destroy and source protection explanations |
| 10 | Multiple targets, direct action and menu | Target counts and readable paths, including another directory, from direct/menu Add |
| 11 | Confirmation pages and terminal resizing | Escaped long paths, final-page cancellation, resize restart and small-pane guidance |
| 12 | git.yazi coexistence | Distinct readable git/chezmoi signs; automatically skipped without `--git-plugin` |

## Results, evidence and isolation

`Files` checks actual contents, existence, script markers and rejected command
invocations. `State` checks authored expectations against internal plugin records;
it is a diagnostic, not proof of physical rendering. `Visual` is your judgment.
Automatic checks never fill in the visual verdict. A step passes only when all
three pass. Results include `PASS`, `FAIL`, `SKIP`, `NOT RUN`, and harness `ERROR`.
A skipped or unfinished step is never presented as a pass.

Each case result comes from its latest attempt. A retry can replace an earlier
case result, but the report preserves the earlier attempt and any failures.
If steps have different results, the case uses this priority: `ERROR`, `FAIL`,
`NOT RUN`, `SKIP`, then `PASS`.

If preparing a step or case fails, the guide keeps your saved verdicts and
position. The message identifies the intended case and step; `W/d` shows the
preparation-error history. Retry the same operation after resolving the cause.
These errors are archived separately from step verdicts and retain fixtures,
even if a later retry succeeds and cleanup was requested.
With `KEEP_FIXTURE=1`, a failed case's retained fixture path also appears in the
preparation-error message and history. Backend diagnostics go to stderr so the
guide can still read its JSON response without changing saved verdicts.

Press `q` to open the exit menu:

| Key in the exit menu | Operation |
| --- | --- |
| `d` | Show results and diagnostics |
| `k` | Save, retain fixtures and exit; use this to resume later |
| `c` | Save and exit; clean fixtures unless a failure or error requires retention |
| Escape | Return to the walk |

You can save before completing all cases; unfinished steps remain `NOT RUN`.
Choose `k` to keep a session resumable. After cleanup, the report survives but
its fixture paths cannot be reopened.

The completed guide replaces step instructions with case-result counts;
these totals describe the latest attempt for each case. The launcher archives
results only after Yazi exits, under ignored
`.dev/manual-runs/<run-id>/`. Evidence includes every attempt, versions, source
hashes, file/state check failures, observations, command arguments and logs.
Any failed attempt, interruption, or archive error retains the fixtures even
if cleanup was requested. Successful cleanup removes only ownership-checked
fixture roots. Saved reports remain available after cleanup.

The fixture does not change normal chezmoi state, Yazi config or dotfiles.
Only named ordinary fixture targets are applied during preparation; pending
scripts are added afterward. The harness wrapper records commands and injects
specified failures. Human rendering checks still require your own terminal;
screenshots, actual editor integration and Linux acceptance are not automated.

### Resume or remove a retained session

After exit, the launcher prints the report path as `Results: ...` and, when
retained, the session root as `Fixtures retained: ...`. Use that session root
for `PATH` below, not the report directory or an individual attempt directory.

```sh
test/manual.py open PATH
```

This resumes the saved case and step only when the recorded Git HEAD, working
tree diff, source hashes, and Yazi/chezmoi versions match the current execution.
Keep the checkout available and unchanged while completing a session. A new
commit, a changed diff/source file, different tool versions, or missing execution
information causes the launcher to refuse resume before changing progress,
rewriting fixture configuration, opening Yazi, or archiving. Start a fresh
`test/manual.py` session after changing code or tools; the old results and
fixtures remain available for inspection, `status` and explicit cleanup.

With matching execution information, the saved step opens with the guide and
key bindings from that checkout. Theme steps capture a fresh status epoch when
reopened; press `Y` as instructed.

The earlier 24-case sessions use different case numbers and cannot be resumed
with this 12-case guide. The launcher rejects that mismatch before changing
saved progress or opening Yazi. Start a fresh `test/manual.py` session; old
reports and fixtures remain available for inspection, `status` or explicit cleanup.

For diagnostics outside the walk, `test/manual.py status PATH` queries its
active chezmoi context. When the session is no longer needed,
`test/manual.py clean PATH` removes the retained session and all its attempts.
Exit every Yazi process using that session before cleaning it. Archived reports
under `.dev/manual-runs/` are preserved.

## Automated verification

Run `test/manual_runtime.py` for the guide's private-tmux integration checks.
They exercise real display, progress, preparation, retries, selection handling,
details and exit; they do not record human visual acceptance. Run
`test/check.py` and `test/runtime.py` for the ordinary development/integration
checks. See [validation](../docs/validation.md) for measured evidence and limits.
