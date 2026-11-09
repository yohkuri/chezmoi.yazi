# Validation

What has been checked, as of the code on `main`: the latest run of each
suite, what each covers, what people checked by hand, what was measured about
the tools around the plugin, and what stays unverified. A change that alters
any of that rewrites the part it alters. What ran for a particular change is
in its pull request, and earlier states of this page are in its history.
Versions are the ones tested, not a compatibility claim.

## Latest runs

On the code of `488412c`, each suite alone, one run each, no reruns:

- macOS 26.6.2 with Yazi 26.9.1, chezmoi 2.74.0, tmux 3.8 and Lua 5.5.1:
  `test/check.py` with 63 core, 126 action policy and 20 main assertions and
  59 Python tests; `test/runtime.py` 16 passes; `test/e2e.py` 6 scenarios;
  `test/manual_runtime.py` 15 passes.
- An Ubuntu 24.04 container on Docker Desktop (aarch64), with Yazi 26.9.1 and
  chezmoi 2.72.2 from their aarch64 release assets and tmux 3.4:
  `test/runtime.py` 16 passes, `test/e2e.py` 6 scenarios,
  `test/manual_runtime.py` 15 passes.

CI runs on every pull request and on pushes other than to Dependabot's
branches. `checks` runs what `test/check.py` runs, adds the status and action
suites under Lua 5.1 and 5.4 and `luac -p` under 5.1, 5.4 and 5.5, and
validates commit messages. `E2E smoke` runs
`test/e2e.py --smoke` on Ubuntu 24.04 (x86_64) with SHA-256-pinned Yazi
26.9.1 and chezmoi 2.72.2. Both passed on `860e4bf`.

## What the suites cover

`test/check.py` never starts Yazi. Its pure suites cover:

- **Status:** path boundaries, NUL framing, XY preservation, malformed or
  out-of-scope status, bounded recovery, own and descendant independence,
  summary disabling, exceptional filenames, and the filters the status
  queries pass before `--`.
- **Actions:** supported flags, invalid selections, recursive target
  reduction, confirmation policy, literal path arguments, shared context,
  matching preview and apply scope, and the rejections of a nonrecursive
  directory destroy and of a destroy target containing the source. No
  argument starting with `--force` reaches any stage of fourteen plans that
  cover each action's options. `actions.facts` is pinned against a fake `run`:
  each action's `managed` queries and their order. The command table's
  destination-root exception is pinned through `actions.prepare`.
- **`test/main.lua`:** `setup`'s `notify_timeout` range, and that
  notifications use it, under stubs for Yazi's globals.

On 2026-11-05, of the single-line mutants of `core.lua`, `actions.lua`,
`main.lua` and `render.lua`, the pure suites killed 79%, 78%, 25% and none.
Those four files have not changed since; the other root Lua files have no
score.

`test/runtime.py` reads plugin state through the probe and checks the screen:

- Managed, unmanaged, clean, `" M"`, `MM` and `" D"`; missing descendant
  summaries, `exact_` removals, `.chezmoiremove`, ignores, symlinks, and
  pending scripts, which stay unexecuted.
- Template evaluation, age-encrypted status, a missing identity, failed
  templates, `C!!`, partial summaries, and recovery.
- Spaces, Japanese text, quotes, backslashes, CR/LF and leading dashes in
  names, through recursive batches and the nonrecursive CR/LF fallback.
- Manual refresh, also during an older generation; directory revisits, tab
  switches, entries added or forgotten outside Yazi, a failed membership query
  and recovery; process counts in a quiet view, with no polling.
- Silent children, early stdout closure, unfinished output, stderr pressure,
  and the timeout, with the direct child gone afterwards.
- Flavor fallback, theme override and reload, wide signs, RGB styles.
- Add and re-add through bindings and the menu; forget keeps the destination
  and destroy removes both; diff before apply, refused and accepted apply,
  chezmoi's conflict prompts, and a failed template stopping before apply.
  Quitting a conflict prompt can exit 0, so the notice reports completion,
  not a count of changed files.
- Recursive and nonrecursive directory add, an orphan symlink whose outside
  referent is neither followed nor created, and edit refused on a directory.
- A nonrecursive directory destroy refused with the directory and its child
  kept, and destroy targets containing the source directory refused, recursive
  or not, with an unmanaged ancestor and in mixed selections.
- Multiple selections, visual select and unset ranges, selections in another
  directory, confirmation pages read back whole at 140x40 and 80x18, a resize
  restarting review, and a 40x12 pane refused.
- Template and encrypted add, encrypted edit leaving the destination alone
  under `edit.apply` and `edit.watch`, the editor's Ctrl-C and failure, and
  cancelled apply keeping the source edit.
- Standalone diff honoring `[diff].exclude`, while apply's preview shows the
  script apply runs.
- The action lock: an obsolete query drains first, no refresh or mutation runs
  while it is held, and target snapshots survive hover movement.
- `support.check_call` over every recorded call at a fixture's end: no
  `--force`, only known queries and actions, and the query flags and filters
  in place. It cannot tell the three `managed` filter pairs apart. The guide's
  fixtures, `test/benchmark.py` and `test/e2e.py` are not read.
- Optionally, git.yazi's linemode beside this one, git's first.

`test/e2e.py` reads neither the probe, the plugin's records nor the command
history: it checks the screen, the exit, fixture files, Yazi's log, tmux's
state, and the recorded answers to Yazi's terminal probe. Its default
run covers status and refresh, the basic commands, navigation, failure
recovery, theme reload and the command edges; `--smoke` runs the first two.
`confirmation-pages`, `source-ancestor` and `visual-selection` run only by
`--case`, since `test/runtime.py` runs the same functions with more checks.

Both suites end `commands` with `terminal_left`. A fixture editor leaves a
color, a hidden cursor, mouse and focus reports, line drawing, a scroll region
and a raw terminal with a queued line, and the check reads the background,
tmux's cursor, mouse and scroll region flags, line drawing through SO and SI,
that the prompt still waits half a second, and the main screen after Enter.
Each of these mutants failed it on macOS and in the container: `process.lua`
as before the runner handled this, the drain removed, no reset, only `\27[0m`,
no SI, no scroll region reset, and the prompt read with echo on. With the
prompt's erase removed it still passes: on Yazi 26.9.1 something on resume
clears the cursor's line, which with echo off is the prompt's (seen, not
traced).

`test/manual_runtime.py` presses the guide's keys in a private tmux. It is an
automated execution check, not a person's walk.

`test/benchmark.py` times the three CLI calls of one recursive acquisition in a
synthetic `.config`. One run on `860e4bf`, macOS 26.6.2 with chezmoi 2.74.0:

| Managed files | Subprocesses | Total CLI time | Managed and status bytes |
| --- | --- | --- | --- |
| 100 | 3 | 0.035 s | 21,997 |
| 5,000 | 3 | 0.157 s | 1,095,097 |

It excludes fixture creation, Lua reduction, rendering, encryption and failed
query recovery, and does not predict a real dotfiles repository. CR/LF targets
need extra queries, and fetcher bursts can start more than one pass. The 2 s
reuse, 8 recovery queries and 10 s timeout are defaults, not measured optima.

## Checked by hand

Recorded only as the person who checked reported it.

- **The guided walk.** The one human walk, on 2026-10-16, was of the earlier
  24-case guide: 22 PASS and two SKIP. Manual refresh was skipped because
  acquisition updated the signs before `R`; git coexistence because no git
  plugin was given. The guide was revised after it, and the current 12-case
  guide has had no human walk.
- **The terminal after a command.** On 2026-11-10 the user checked the code of
  `488412c`, as `39e3778` before the rebase merge, in Ghostty 1.4.0 outside
  tmux, on macOS 26.6.2 with Yazi 26.9.1 and chezmoi 2.74.0, in a throwaway
  setup whose editor left a red background, a hidden
  cursor, mouse, focus and bracketed paste reports, kitty's first flag,
  modifyOtherKeys 2, line drawing, a scroll region and a raw terminal, and
  whose pager waited 5 s. The user reported every step fine: at the prompt no
  red, a visible cursor, a drag selecting text, focus changes doing nothing,
  and one Enter returning; Enter typed during the pager dropped; Ctrl-C at
  apply's prompt reporting failure without the apply confirmation; and after
  quitting, a normal shell with the diff's output and no prompt. That last
  step came after Yazi's own exit, so it does not tell the plugin's line
  drawing and scroll region resets from Yazi's; tmux checks those. No step
  would have shown kitty's first flag, modifyOtherKeys or a focus report left
  on: none changes a plain Enter, and the prompt does not echo.
- **Kitty keyboard flags and modifyOtherKeys.** On 2026-11-10, on `860e4bf`
  and the same setup, the user first saw Ctrl-C arrive at a shell's `read` as
  an escape sequence under kitty's first flag and under modifyOtherKeys 2,
  so Ghostty honored both. Then, with an editor leaving one of them on, Ctrl-C
  at the prompt returned to Yazi with the failure notice, for each. The
  sequences received were not recorded.
- **The README picture.** `docs/images/readme.png` is the user's screenshot of
  `test/readme.py` in Ghostty 1.3.1 on macOS 26.6.2, taken on 2026-10-27 at
  100x21 with the font at 28pt, 1417x740 pixels. How it looks was judged by
  eye. The scripted checks of `test/readme.py`, such as resizing, signals and
  a failing chezmoi, ran only in a private tmux.

## Measured about the platform

### Yazi outliving its terminal

On 2026-10-21, on macOS 26.6.2, Yazi was opened in a private tmux, a plugin's
entry made one call, and `tmux kill-server` closed the terminal while it ran.
With the entry waiting in `ya.confirm`, Yazi kept running: 3 of 3 runs through
the harness, and 9 of 9 without it or this plugin, six on 26.9.1 and three on
the nightly `7c45837`. Through the harness, it exited within 0.1 s with no
call, in `ya.sleep(15)` or in `ya.input`, and stayed through a busy loop until
the loop ended. Without the harness, checked at 10 s, it had exited in
`ya.input` (4 of 4 runs), `ya.which` (2 of 2) and Yazi's own remove
confirmation (4 of 4). SIGTERM did not end the leftover. In an empty
directory Yazi exited at `ya.confirm` in 3 of 3 runs; why files matter was not
traced.

Read off the 26.9.1 source, not traced in a debugger: when the terminal is
gone, a draw fails and the main loop returns before the hangup's quit exits.
Dropping the tokio runtime then waits for every `spawn_blocking` task, a
plugin's entry runs in one, and the token `ya.confirm` awaits completes only on
an answer. Yazi stops reading signals after a hangup, quit or terminate
signal. Not tried: a real terminal window closed at the prompt, and Linux.
`support.stop` kills such a leftover ten seconds after the tmux server stops.

### Yazi's terminal probe

Read off the 26.9.1 source (`yazi-emulator/src/probe.rs`, and `report.rs`,
`stop.rs` and `quit.rs` in `yazi-actor/src/app`): once tmux's XTVERSION names
it, Yazi re-sends DA1 through tmux passthrough, and `app:stop`, which
`ui.hide` reaches, and `app:quit` each wait up to 5 s for the answer. A
detached tmux has no terminal to answer, so each command screen and each quit
paid that wait: a plain `q` took 5.04 s in 3 of 3 runs, and as long in two
runs inside a second detached tmux. `test/da1.py` answers it in every pane the
harness opens, and a run that opened a pane but recorded no answer fails.

### Claude Code's path rules and the Lua hook

On 2026-10-20 and 2026-10-21, fresh `claude -p` sessions of Claude Code
2.1.304 on macOS, loading only project settings, read one file each, and the
checks read the transcripts and hook events, not the replies. `*.lua` in a
rule's `paths` matched Lua below the root too; `/*.lua` matched `core.lua` and
not `test/core.lua`, and `./*.lua` neither. From the main checkout and from a
worktree under `.claude/worktrees/`, a session attached the rules of the
checkout it worked in. After one `Edit` of `core.lua`, the `PostToolUse` hook
formatted it, and with the `stylua` line gone from `mise.toml` it exited 2 and
the session received its message as a blocking error. Not run: `Write`, an
interactive session, other platforms, and sessions loading user or local
settings.

### The screen cleared before each stage

Each stage starts with `\27[2J`. Recorded with the change merged as `c9bb335`
on 2026-11-06: in a herdr 0.9.5 tab
on Ghostty, with 300 lines printed by `seq` before the first action, 225 of
them stayed in the scrollback. The Ghostty version was not recorded, later
stages were not measured, and no other terminal was.

### chezmoi destroying an ancestor of the source

On 2026-10-03, through the plugin before it refused destroy targets containing
the source directory, in a disposable fixture with chezmoi 2.73.0 and the
source directory at `.local/share/chezmoi` under the destination, a recursive
destroy of `.local` removed an unrelated source entry once its first prompt
was accepted, while that entry's destination remained.

### Installing with ya pkg

On 2026-10-26, with Yazi 26.9.1 on macOS and empty `YAZI_CONFIG_HOME` and
`XDG_CACHE_HOME`, `ya pkg add yohkuri/chezmoi` installed the six root Lua
files, `README.md` and `LICENSE`, and not `docs/`, so an installed README's
links into `docs/` lead nowhere offline. `ya pkg delete` removed it. Over a
`plugins/chezmoi.yazi` placed by hand, a copy or a symlink to a clone,
`ya pkg add` stopped with "You have modified the contents" and left it alone.
Yazi was not started on the installed copy.

## Tooling without tests

These keep no tests, so what was run by hand is their evidence.

- **`.githooks/`.** On macOS with Git 2.54.0, `pre-commit` refused a commit on
  `main` with no `origin`, this repository's URL or a fork, and allowed other
  branches, a detached HEAD and `CHEZMOI_YAZI_COMMIT_ON_MAIN=1`. `pre-push`
  refused a push to `refs/heads/main` for eight spellings of the GitHub URL
  and allowed a fork, a lookalike host and other refs. In clones with the
  hooks installed by the two lines the README then gave, a real commit and
  `git push --dry-run` were refused through a global `core.hooksPath`. On
  2026-11-10, with Git 2.54.0 and no global Git configuration, the three lines
  that "Install the git hooks" in `CONTRIBUTING.md` now gives installed both
  hooks in a clone, from a linked worktree into the shared directory, and in a
  clone without `.git/hooks`. In each, `pre-commit` then refused a commit on
  `main` with its own message; a commit on another branch in the worktree went
  through, and a second install was refused. The match is by suffix, so a
  local path ending in `github.com/yohkuri/chezmoi.yazi` is refused too and an
  SSH host alias is not recognized. Not run: without `core.hooksPath`, Linux.
- **`scripts/format-lua-hook.sh`.** On 2026-10-19 the version then, which
  read StyLua's pin from `check.yml`, ran with sample payloads: it formatted
  Lua at the root, in a subdirectory and in a linked worktree, through `/tmp`
  and `/private/tmp`, left alone Lua under `.github/`, `.git/`, ignored
  directories, other repositories and hidden files, and exited 2 without
  changing the file without `jq`, Git or `stylua`, on a StyLua version other
  than the pin, and on a syntax error. The current version, which reads
  `mise.toml` and runs StyLua from the edited file's checkout, ran by hand
  once from another directory, where it formatted a real file, and in the
  Claude Code sessions above. A version mismatch and a `PATH` set by
  `mise activate` have not been run against it.
- **The skill link checker.** Of `test/test_skills.py`, only
  `test_repository`, which checks this checkout's links, is left. Until
  2026-11-05, fixture cases that every `test/check.py` ran checked that
  `problems()` reported a missing link, a copied file, a wrong relative
  target, a link to a missing or Git-ignored skill file, a correct link Git
  ignores, and a link to a skill directory or the whole skills directory,
  each exactly once, and passed correct links holding a space or Japanese
  text.
- **`test/all.py`.** In scratch runs, one failing suite failed the run, each
  output came whole, a suite that could not start was reported failed, and on
  SIGINT to its process group it waited for the suites' cleanup and exited 1.
  It now exits 130 when interrupted, which no run has shown, and it has not
  run with a real suite failing or interrupted.
- **Commit validation and its range.** `scripts/check-commits.sh`,
  `scripts/check-ascii.lua` and the range `check.yml` passes them have no test
  under `test/`. On 2026-09-20, eight valid and invalid messages, among them
  length, capitalization, body spacing and a body emoji, and three commit
  ranges in an isolated Git repository, one holding an invalid commit, gave
  the expected results. On 2026-10-03, in an isolated single-branch clone, the
  workflow's shell block passed a normal push, a force push whose previous head
  was unreachable, a new branch and a pull request, and refused an invalid
  commit with the push base missing.
- **`.github/workflows/tag.yml`.** It has run and passed on each push to
  `main`, most recently `860e4bf`; `@since` has not moved since it was added,
  so it has tagged nothing and no tag exists. Its tagging path ran only under
  macOS's bash 3.2.57 in a clone with a local bare origin. No
  `rev = "=yazi-<version>"` pin has been tried.
- **The `re2js` override.** `package.json` pins `re2js` 2.8.7 under
  `markdownlint@0.42.0` for GHSA-gg6h-894w-4m9c. Its key names that version,
  so a `markdownlint` update leaves it unapplied, as a stand-in key showed with
  `npm install --package-lock-only`. A file with planted violations still
  reported MD011, MD013 and MD039 on 2.8.7.
- **CI's failure path.** `actions/upload-artifact` v7 runs only when
  `E2E smoke` fails and has not run. No Dependabot pull request has come
  through `.github/dependabot.yml`.

## Unexplained and known windows

- With `Runtime.key`'s 0.1 s settle removed, `test/e2e.py` lost a key that
  followed a `g` chord once in three runs, and the guide failed in each of
  three at a key following its digit keys. The settle stays.
- While a screen clear after the prompt was in, until 2026-11-06, with
  `ya.sleep(0.7)` after it, `command-edges` lost the `v` after Ctrl-C in 7 of
  20 runs, the wait timing out with Yazi on the screen; and once, with no
  delay, a `q` sent through `herdr pane send-text` right after the redraw did
  nothing. Neither was tried after the clear went, and no suite run since has
  failed this way.
- A known window, not seen without an injected delay: `ui.hide` shows the last
  command's screen until the next command clears it, so the waits on the
  fixture editor's text in `command-edges` (`test/action_cases.py`) and in
  `foreground_launcher`'s second round (`test/manual_runtime.py`) can match the
  previous run's text. With `ya.sleep(0.3)` after `ui.hide` in a scratch copy,
  both sent Ctrl-C before the new editor started and failed. The wait before
  `Native edit applied before preview` has the same window, by reading the
  code.
- A hypothesis, not seen: the Yazis of suites run together share one DDS
  socket under `$TMPDIR`, so one quitting could hand the server over while
  `test/runtime.py` sends `ya emit-to`.

## Not verified

- Linux beyond the aarch64 container above and CI's x86_64 smoke run; the
  guided walk and git.yazi coexistence on Linux; Windows, which `setup`
  rejects; other Yazi releases and chezmoi versions than those above.
- `--git-plugin` in full since the command actions were added; only
  `test/runtime.py --git-plugin --case visual-selection`, which adds `status`,
  ran since, with git.yazi `f703392` on 2026-10-24.
- A human walk of the current guide, and readability across fonts, colors,
  grapheme combinations, very long lists and hovered rows.
- For the terminal state after a command, real terminals other than Ghostty
  1.4.0 on macOS outside tmux, including Ghostty inside tmux; and the
  bracketed paste, focus and X10 mouse resets, which tmux exposes no state for
  and no hand check showed.
- The fallback restore inside Yazi; only the snippet ran by itself.
- The scripts without mise since `test/check.py`'s analyzers were pinned in
  `mise.toml`; the last run without it, on 2026-09-20, predates the pins.
- Not handled, by reading the code: a command that leaves `O_NONBLOCK` set or
  stays in the alternate screen, and a pane narrower than the prompt, which
  keeps the prompt's upper rows.
- Real editors, GUI editors and their wait conventions, pagers, interactive
  secret providers, arbitrary hooks, and terminal sizes other than those
  above.
- Grandchildren of a timed-out query: the deadline covers the direct child
  only. The output cap applies after line reads, so one long line can
  allocate more than the cap for a while.
