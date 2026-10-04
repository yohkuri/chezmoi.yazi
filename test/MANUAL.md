# Guided manual acceptance

Launch from the repository root in an interactive terminal:

```sh
test/manual.py
```

Yazi opens directly in the same terminal. Follow the bottom guide; press `W`
for controls or full instructions. Fixture edits, failure injection, checks,
retries, results and cleanup are handled from this session. You do not need
another terminal, shell commands after launch, or an external checklist.

## Requirements

Have Yazi 26.9.1+, chezmoi and uv on `PATH`. The executable launcher uses the
locked uv environment; no pip packages, Neovim or tmux are needed for this walk.
Keep the checkout and its `.venv` in place until the session ends. A terminal
at least 100 columns wide is convenient; smaller sizes are acceptance cases.
Public UI and instructions are English. Unicode filenames are intentional.
Linux and every font/terminal combination are not established by this guide.

Optionally include an existing, read-only git.yazi checkout at startup:

```sh
test/manual.py --git-plugin /absolute/path/to/git.yazi
```

Without it, the coexistence case is recorded as `SKIP` with a reason.

## Walking a case

The guide shows the case, step, operation and expected display. Long text can
be clipped; `W`, then `d` shows the complete instruction and diagnostics in the
same terminal. Enter advances that viewer, `b` goes back, and `q` then Enter
returns to Yazi. It also lists every case number and current result.

1. Perform the indicated operation using normal Yazi navigation or the fixture
   keys below. Preparation formerly done with `cp`, `printf` or `rm` happens
   when you enter the step. Press `R` or `Y` yourself when instructed.
2. Inspect the visible result. Press `W`, then `p` to record visual `PASS` and
   run the file/state checks; use `f` for a failure or `s` to skip with a reason.
3. Press `W`, then `n` for the next step. Unanswered observations cannot advance.
   Recorded failures can advance so the rest of the walk remains usable.
4. Use `W`, then `r` to retry the current case from a fresh fixture, or `j` to
   enter a case number. Previous attempts remain available as evidence.

Each case and retry has a new source, destination, database and command cache.
Steps within a case share those paths. Changing cases clears selection, closes
extra tabs and restores the baseline theme. Opening guide controls preserves
ordinary and visual selections. Guide transitions and actions are serialized;
wait for the current command to return before recording or changing cases.

The four-row guide sits above the ordinary status bar; short terminals get a
one-row guide. `W`, then `h` hides/restores it. Hidden mode restores Yazi's normal
layout and keeps `W` available. Hide it for normal-layout resize/small-pane tests.
Modal confirmations appear above the guide.

## Keys

Keys are case-sensitive. These overrides affect only the disposable session.

| Key | Operation |
| --- | --- |
| `W` | Guide controls |
| `q` | Results/exit menu; Escape returns to the walk |
| `j`, `k`, arrows, `h`, `l` | Normal navigation |
| Space | Toggle hovered selection without moving |
| `S` | Clear committed selection |
| `v`, `V` | Normal visual select/unset |
| `C` | Real chezmoi action menu |
| `R`, `Y` | Refresh status / reload theme |
| `a`, `r`, `e`, `E` | Add / Re-add / Edit / Edit and apply |
| `d`, `p`, `f`, `x` | Diff / Apply / Forget / Destroy |
| `D` | Destroy with `--recursive=false` |
| `t`, `z` | Add as template / encrypted Add |
| `N`, `B` | Enter `.config` / destination root |
| `G`, `H` | New `.config` tab / tab zero |
| `1`, `2`, `3` | Reveal `range-a` / `menu-a` / `.config/outside` |
| `4` | Select all long/deep confirmation targets |
| `5`, `6`, `7`, `8`, `9`, `0` | Reveal `.local` / `source` / `unmanaged` / `clean` / `.config` / `.exact` |
| `T` | Write the internal diagnostic probe |

Commands use real chezmoi and its native prompts, with no forced confirmation.
Read output and press Enter when the command asks to return to Yazi. For Apply,
return from the diff first, then answer the plugin confirmation. Destructive
commands can also have a native chezmoi prompt after plugin confirmation.

Edit cases use a disposable terminal editor displaying the current source.
Type the instructed replacement line and Enter to save; Ctrl-C interrupts it.
It requires no personal editor configuration. Encryption uses a public test age
identity inside the fixture; it is never suitable for real secrets.

## Cases and previous checklist coverage

Instructions and expectations live in `test/manual_cases.py`; this document
explains the workflow without duplicating the complete step list.

| Cases | Coverage from the former checklist |
| --- | --- |
| Membership and status | Section 1: clean/modified/unmanaged/ignored/symlink/removal, missing and exact-directory summaries, no background script execution |
| Names, alignment and colors | Section 2: spaces, Unicode, quotes, backslashes, dash, newline/CR, hover/selection, resizing |
| Manual refresh | Section 3: resolve and restore a local edit |
| Membership discovery and removal | Section 4: external source addition/removal |
| Template failure and recovery | Section 5: isolated failure, repair, partial directory underline and recovery |
| Membership query failure | Section 6: fail-managed and recovery |
| Navigation and tabs | Section 7: source edit while away, revisit and tab switch |
| Theme override and flavor fallback | Section 8: precedence, wide sign, color, restore and unchanged epoch |
| Add, Re-add and Forget; Destroy | Section 9.1–2: direct/menu actions, cancel, native approval, destination retention/removal, shallow-directory rejection |
| Scoped Apply | Section 9.3: diff, decline, accept, unchanged unrelated script |
| Template Add; encrypted Add | Section 9.4: template preservation and disposable credentials |
| Mixed selection rejection; cross-directory selections | Section 9.5: complete selection, mixed targets and directory Edit rejection |
| Plain Edit; Edit and Apply; editor interruption | Section 9.6: config apply/watch override, retained source after cancellation, accepted apply, Ctrl-C and restored terminal |
| Diff and pending script | Section 9.7: preview and deliberately scoped script execution |
| Confirmation pages | Section 9.8: long/deep/Unicode/control paths, later-page cancellation, resize restart and too-small pane |
| Visual range and unset; source protection | Additional regressions: direct/menu range capture, guide selection preservation, source directory and its ancestors |
| git.yazi coexistence | Section 1: `"G "` preceding chezmoi signs without hiding them |
| Results and exit | Section 10: evidence, retained failures and ownership-checked cleanup |

## Results, evidence and isolation

`Files` checks actual contents, existence, script markers and rejected command
invocations. `State` checks authored expectations against internal plugin records;
it is a diagnostic, not proof of physical rendering. `Visual` is your judgment.
Automatic checks never fill in the visual verdict. A step passes only when all
three pass. Results include `PASS`, `FAIL`, `SKIP`, `NOT RUN`, and harness `ERROR`.
A skipped or unfinished step is never presented as a pass.

Press `q` and choose to save and retain fixtures, or save and clean them. The
launcher archives results only after Yazi exits, under ignored
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

For recovery after interruption, the launcher prints the retained session root.
Advanced helpers remain available: `test/manual.py open PATH` resumes its saved
case and step; `test/manual.py status PATH` queries its active chezmoi context;
`test/manual.py clean PATH` removes the retained session and all its attempts.
Do not clean while any Yazi process uses that session.

## Automated verification

Run `test/manual_runtime.py` for the guide's private-tmux integration checks.
They exercise real display, progress, preparation, retries, selection handling,
details and exit; they do not record human visual acceptance. Run
`test/check.py` and `test/runtime.py` for the ordinary development/integration
checks. See [validation](../docs/validation.md) for measured evidence and limits.
