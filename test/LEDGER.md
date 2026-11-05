# Test ledger

Every test in this repository, what it protects, where tests repeat each
other or depart from the paths the plugin really takes, and which ones are
worth little. Measured on 2026-11-05 on the checkout at `a52116c`; the
numbers below are from that run, and the verdicts are a reading of the
code against them. Each verdict is a proposal, not a change: nothing was
removed.

## How the ledger was measured

Everything ran on Ubuntu 24.04 in a container with 4 cores: Yazi 26.9.1
and chezmoi 2.72.2 from the release binaries `check.yml` pins, tmux 3.4,
Lua 5.4.6 (`lua5.4`, since no Lua 5.5 package was at hand; `test/check.py`
runs the pure suites with the Lua 5.5.1 that `mise.toml` pins), uv 0.11.32
and Python 3.14.6. This is the first recorded run of the full runtime, E2E
and guide suites on Linux; CI runs only `test/e2e.py --smoke` there. One run
each, in this order, every one passing and leaving no fixture or Yazi:

| Command | Result | Time |
| --- | --- | --- |
| `lua5.4 test/core.lua` | 63 assertions | 0.01 s |
| `lua5.4 test/actions.lua` | 126 assertions | 0.01 s |
| `lua5.4 test/main.lua` | 20 assertions | 0.01 s |
| `uv run --locked python -m unittest discover -s test -p 'test_*.py'` | 88 tests | 4.5 s |
| `test/e2e.py --smoke` | 2 scenarios | 6 s |
| `test/runtime.py` | 7 cases, 16 PASS lines | 62 s |
| `test/e2e.py` | 9 scenarios | 42 s |
| `test/manual_runtime.py` | 15 PASS lines | 89 s |
| `test/benchmark.py` | 2 measurements | 1 s |

Not run: `test/check.py` as a whole, since lua-language-server, StyLua and
ShellCheck were not installed (markdownlint ran on this file through the
locked npm tools); `--git-plugin` anywhere; `test/readme.py` and
`test/manual.py`, which need a person at a terminal. The guide suite ran
while a two-worker mutation run and an `npm ci` shared the machine, and
the other suites alone; nothing needed a rerun.

Two kinds of evidence back the verdicts besides reading the code:

- **Mutation analysis of the pure suites.** A script, not kept, made 1,122
  single-line mutants of the six root Lua files (operator flips such as
  `==`/`~=` and `and`/`or`, dropped `not`, `true`/`false` swaps, `+ 1` to
  `+ 2`, small constants, error strings on `return` lines, and the deletion
  of each simple statement), kept those that still compiled, and ran each
  pure suite against each mutant with a recording `assert`, so that every
  failing assertion site was seen rather than only the first. From the
  kill sets it computed each site's unique kills and a greedy minimal set
  of sites that kills the same mutants as the whole suite. A site with no
  unique kills is one the mutants cannot tell from its neighbors; it may
  still pin a contract the operators above cannot break, so that is a
  flag, not a verdict on its own.
- **Five targeted plugin mutations against the Yazi-driven suites**, run
  from a copy of the checkout, to see which suite notices a change the
  pure suites let through.

### Mutants killed by the pure suites

| File | Mutants | Killed by its own suite | Killed by any pure suite |
| --- | --- | --- | --- |
| `core.lua` | 333 | 264 (79%), `test/core.lua` | 273 (82%) |
| `actions.lua` | 251 | 197 (78%), `test/actions.lua` | 201 (80%) |
| `main.lua` | 255 | 64 (25%), `test/main.lua` | 64 (25%) |
| `interaction.lua` | 123 | no suite of its own | 11 (9%) |
| `process.lua` | 96 | no suite of its own | 1 (1%) |
| `render.lua` | 64 | no suite of its own | 0 |

`test/actions.lua` kills 9 `core.lua` mutants that `test/core.lua` misses,
all in `core.context` and in the flags of `core.list_managed`, because it
pins the exact query strings and `test/core.lua`'s fake `run` does not.
`test/main.lua` kills 4 `actions.lua` mutants of the `remove` and unknown
command messages that `test/actions.lua` checks only as `nil`. Greedy
covers: 32 of `test/core.lua`'s 58 killing sites kill everything the suite
kills, 41 of `test/actions.lua`'s 65, and 8 of `test/main.lua`'s 9.

### Targeted mutations against the Yazi-driven suites

Each row changed one line of the plugin in a copy of the checkout and ran
the suites named; "pure" is all three pure suites.

| Change | pure | runtime | e2e | guide |
| --- | --- | --- | --- | --- |
| E1 `actions.lua`: "Not managed by chezmoi" reads "Not handled by chezmoi" | pass | FAIL `command-edges`, "mixed selection rejection" | FAIL, same | pass |
| E2 `actions.lua`: `add` drops `--template` and `--encrypt` from argv | pass | FAIL `command-edges`, no `clean.tmpl` | FAIL, same | FAIL, Add case's template check |
| E3 `main.lua`: the 30-second dedupe of the status warning becomes 0 | pass | pass `status` | not run | not run |
| E4 `core.lua`: `partial` is `changed or not complete` | pass | pass `status` | pass `status-refresh` | FAIL, "partial" stays set after repair |
| E5 `actions.lua`: apply and its preview lose `--include=all --exclude=none` | pass | FAIL `command-edges`, "pending.sh" absent from the preview | FAIL, same | not run |

E1's guide run passed because its wait, `"Not managed" in s`, is met by
the guide's own instruction text, which names the warning before the key
is pressed; the step's `no_action="edit"` check still shows no editor
opened. E3 passed everywhere: nothing asserts how often the status
warning shows. E4 is a `core.lua` logic slip that only the guide catches,
through its `partial: False` expectation after the repair in the Warnings
case.

## Inventory

| File | Kind | Protects | Runs in | Time here |
| --- | --- | --- | --- | --- |
| `test/core.lua` | pure Lua, 63 assertions | `core.lua`: path rules, NUL and status parsing, chunking, discovery, `collect` | `test/check.py`; CI also under Lua 5.1 and 5.4 | 0.01 s |
| `test/actions.lua` | pure Lua, 126 assertions | `actions.lua`: option parsing, preflight rejections, target reduction, argv, confirmation policy, `facts` queries | `test/check.py`; CI also under 5.1 and 5.4 | 0.01 s |
| `test/main.lua` | pure Lua with stubbed Yazi globals, 20 assertions | `main.lua` `setup`'s `notify_timeout` and the timeout of three notification paths | `test/check.py`; CI's Lua 5.1 and 5.4 runs skip it | 0.01 s |
| `test/test_support.py` | Python unit, 8 tests | harness helpers: Lua serializer, byte I/O, `owned`, `stop`, `da1.answer`, `check_call`, cleanup retry | `test/check.py`, CI | 2.7 s |
| `test/test_screen.py` | Python unit, 9 tests | `test/screen.py`, the parser E2E and the action cases read the screen with | `test/check.py`, CI | 0.01 s |
| `test/test_manual.py` | Python unit, 39 tests | `test/manual_backend.py` and `test/manual.py`: the guide's state machine, archive and launcher | `test/check.py`, CI | 0.3 s |
| `test/test_readme.py` | Python unit, 13 tests | `test/readme.py`'s reading of the README's blocks | `test/check.py`, CI | 0.01 s |
| `test/test_skills.py` | Python unit, 3 tests | the symlinks from `.claude/skills` to `.agents/skills` | `test/check.py`, CI | 0.04 s |
| `test/test_githooks.py` | Python unit, 10 tests | `.githooks/pre-commit` and `pre-push` | `test/check.py`, CI | 0.4 s |
| `test/test_format_hook.py` | Python unit, 3 tests; skipped without jq | `scripts/format-lua-hook.sh` | `test/check.py`, CI | 0.3 s |
| `test/test_all.py` | Python unit, 3 tests | `test/all.py`'s output ordering and exit codes | `test/check.py`, CI | 1.2 s |
| `test/runtime.py` | Yazi in tmux, probe and command wrapper, 7 cases | the plugin's records, calls, rendering and actions | by hand | 62 s |
| `test/e2e.py` | Yazi in tmux, screen only, 9 scenarios plus `git-coexistence` | rendering and actions as a user sees them | `--smoke` in CI; the rest by hand | 42 s |
| `test/manual_runtime.py` | Yazi in tmux, 6 functions | the guide that `test/manual.py` runs, and the plugin flows it drives | by hand | 89 s |
| `test/benchmark.py` | measurement | timings of the three queries; asserts only output line counts | by hand | 1 s |
| `test/readme.py`, `test/manual.py` | tools for a person | the README picture; the human walk | by hand | n/a |

The rest of `test/` is harness, not tests: `support.py`, `command.py`,
`child.py`, `da1.py`, `editor.py`, `screen.py`, `action_cases.py`,
`manual_backend.py`, `manual_cases.py`, `probe.lua`, `runner.lua`,
`manual.lua`, `manual_types.lua`, `manual-theme.toml`, `check.py`,
`all.py`, `MANUAL.md` and `.luarc.json`.

## Pure Lua suites

The tables name assertion sites by line. "Kills" is how many of the
mutants in scope the site failed on, and "unique" how many no other site
in the same suite failed on.

### test/core.lua

| Lines | Assertions | Protects | Kills (unique) | Note |
| --- | --- | --- | --- | --- |
| 10-13 | 4 | `core.path`: `.` and `..`, a non-local URL, NUL, a backslash kept literal | 13, 4, 3 (1), 10 | the backslash case only documents; overlaps the others |
| 14-16 | 3 | `core.inside`: `/ab` is not under `/a`, `/a/b` is, `/` holds everything | 3, 10, 10 (3) | line 16's root case is the one the others cannot replace |
| 17-21 | 6 | `core.managed`: a valid NUL stream, and five malformed ones rejected | 29 (the setup `assert`), 2, 14 (11) | high; each rejection is a distinct branch |
| 22-33 | 7 | `core.status`: a valid line, and six malformed or out-of-scope ones | 16 (16), 9 (7) | high |
| 34-35 | 2 | the exceptional single-path query for a newline name | 4 (3), 5 (5), 3 (2) | high |
| 36 | 1 | `core.chunks` splits by byte budget | 10 | weak on the chunk arithmetic; mutants of `> budget` and `+ 1` survive |
| 41-47 | 3 | `core.dirs`: one template for both directories, normalized | 6 (the setup `assert`), 1, 2, 0 | line 47 pins the template string itself; no operator here could change it, so its 0 kills say nothing |
| 48-51 | 5 | malformed discovery output; the run error passed through | 5 (3), 0 | line 51 has no kills: the same break aborts the suite at the next index; documentation only |
| 123-129 | 7 | the first `collect` pass: XY of a clean, locally edited and unmanaged file, a directory's own XY and `changed` summary, no error, one batch | 35, 38, 8 (2), 35, 49, 37, 30 | heavy overlap, as every assertion reads one pipeline; each names a different field of the contract |
| 132-133 | 2 | a resolved change and summary clear on the next pass | 32, 43 | keep |
| 136-139 | 4 | a broken child: independent file recovered, own status kept, summary `error`, error `exit` | 48, 48, 26, 49 (2) | keep |
| 142-143 | 2 | `partial` with a confirmed change and a failed sibling | 61, 63 (2) | keep; see E4 for what it does not pin |
| 146-148 | 3 | `directory_summary = false`: no summary, own XY, no error from an unrelated broken child | 1 (1), 36, 33 | keep |
| 154-157 | 4 | a newline descendant forbids recursive line parsing; no empty query | 32, 45 (12), 5 (4), 4 | line 157 (`empty_queries == 0`) is a design promise `chunks` makes structurally; low mutation value |
| 160 | 1 | no status query without managed targets | 0 | cannot fail given `chunks` of an empty list; documents design.md's promise |
| 167 | 1 | bounded subdivision, `<= 4` calls | 5 | written as `equal(x <= 4, true)`, so a failure hides the count |
| 169-170 | 2 | spawn failure gives `error` membership and the `spawn` category | 0 and abort (2), 2 (1) | keep |
| 186-190 | 3 | a timed-out chunk does not stop the next; a cancelled one does; `cancelled` is reported | 34 (2), 28 (1), 34 (2) | regression for the 2026-10-22 fix; keep |
| 199-200 | 2 | recovery respects the byte budget and the retry budget | 6 (1), 8 (3) | both in boolean form; keep, but name the counts |
| 201 | 1 | every query names `--include=all --exclude=none` and no other filter | 4 (4) | review-driven; keep |

Mutants that survive `test/core.lua` and matter: the chunk arithmetic
(lines 69-76 of `core.lua`), `retries - 1`, `math.ceil(#all / 2)`,
`i <= mid`, the `recovery` flag of each `execute` call, `partial` (E4),
and every `return nil, "parse"` category in `managed` and `status`, which
the suite checks only as `nil`.

### test/actions.lua

| Lines | Assertions | Protects | Kills (unique) | Note |
| --- | --- | --- | --- | --- |
| 24-37 | 10 | `parse` rejects `remove`, unknown commands and every unsupported option | 11 (4) | keep |
| 38-40 | 3 | the default `refresh`, Yazi's string booleans, combined add options | 0, 4 (1), 4 | line 38's break aborts the suite one line later; fine |
| 41-43 | 3 | empty selection, mixed selection, directory edit rejected | 3 (1), 12, 7 (1) | keep |
| 44-64 | 5 | nonrecursive destroy of a directory, alone and mixed, and of a source directory, alone and mixed; recursive destroy accepted | 14, 14, 14, 14, 43 | the two mixed-selection variants (48, 57) kill exactly what the plain ones kill; they document all-or-nothing |
| 65 | 1 | a source-tree target | 6 (1) | keep |
| 66-75 | 8 | only recursive re-add, diff and apply may target the destination root, not when nothing is managed, and never forget | 40 (4), 16, 12, 5 | regression for the shared-queries refactor; keep |
| 76-99 | 14 | a destroy target that contains the source directory is rejected whatever the recursion, only for destroy, and siblings or similar prefixes pass | 41 (2), 43, 45 | keep |
| 100-108 | 6 | destination escape, normalization first, a non-local URL, managed but not editable, a vanished file, a special file | 7, 8, 6 (1), 9 (1), 7 (1), 6 (1) | keep |
| 109-123 | 3 | a recursive parent absorbs its child and duplicates; sibling prefixes and newline directories stay apart; nonrecursive keeps the child | 22 (3), 20 (1), 16 (2) | keep |
| 124-130 | 6 | confirmation policy: single add no, directory add yes, forget and destroy always, nonrecursive file destroy allowed, edit direct | 5 (3), 8 (3), 6, 6, 11 (2), 1 | lines 126-127 kill the same six; line 130 adds one; all cheap |
| 131-146 | 16 | eight special names stay literal arguments after `--`, with the context flags apart | 13 (2), 4 (4) | keep; it never looks for `--template` or `--encrypt` in that argv (E2) |
| 147-155 | 4 | edit passes `--apply=false --watch=false`, plain edit matches, preview and apply match, no query flags in an action | 8 (4), 2 (1), 13 (2), 0 | line 155 cannot fail today: `actions.args` never adds query flags |
| 156-183 | 1 | no `--force` in any stage of fourteen plans | 0 | cannot fail today; `support.check_call` repeats it on every recorded runtime call |
| 184-242 | 40 | `facts`: for eight commands, the exact `managed` queries after discovery, in order, and each result in its own field only when queried | 30, 22, 0, 9 (2) | the exact-sequence check (227) kills nothing the fake `run`'s refusal of unknown queries does not; it still pins order and count |
| 243-252 | 4 | each failing query names its message and "No action was run" | 12 (7) | keep |
| 253-254 | 2 | `display` escapes controls; apply's summary names its direction | 1 (1), 3 (3) | keep |

Mutants that survive `test/actions.lua` and matter: every rejection
`why` string except the source-ancestor one, `broad` for several files
with no directory, the `--template` and `--encrypt` flags, apply's and the
preview's `--include=all --exclude=none` (E5), and the summary's
`[including descendants]` and `[directory only]` suffixes.

### test/main.lua

| Lines | Assertions | Protects | Kills (unique) | Note |
| --- | --- | --- | --- | --- |
| 32, 58 | 2 | the default `notify_timeout` of 7, before and after an entry | 0 | no operator changed the 7; fine |
| 33-39 | 9 | seven invalid values rejected by name, both ends of the range accepted | 11 (7), 5 (2) | keep |
| 43-55 | 9 | a parse error, a target-less action and a refused action each notify with the configured timeout | 10, 25 (18), 14 (6) | line 52's count check kills nothing the next two miss; cheap |

The suite reaches 25% of `main.lua`'s mutants and almost nothing of
`interaction.lua`, `process.lua` and `render.lua`; that is its design,
and the Yazi-driven suites hold the rest.

## Python harness tests

Each row: what the test protects, what it overlaps, and a verdict. These
tests protect the harness and the tooling, not the plugin; their value is
the harness's own correctness.

### test_support.py

| Test | Protects | Overlap | Verdict |
| --- | --- | --- | --- |
| `test_lua_string_roundtrip` | `support.lua` writes fixture values Lua reads back byte for byte; needs `lua` on `PATH` | `test_manual.test_lua_serializer_handles_nested_case_arrays` | keep |
| `test_binary_text_roundtrip` | `write` and `read` keep CR, LF and NUL | none; the functions are one-line wrappers | low: cannot fail unless someone adds normalization |
| `test_owned_marker_and_symlink` | the fixture-ownership guards and `stop`'s socket check | none | keep, it guards deletion |
| `test_da1_counts_each_query_once_across_reads` | `da1.answer` over every chunk size | none | keep |
| `test_check_call` | the call oracle, with 14 ways past an earlier version | none | keep |
| `test_stop_kills_only_what_outlives_the_server` | leftover Yazi after the tmux server stops; 2.4 s, needs tmux | none | keep; the slowest unit test, for the leftover Yazi found behind weeks of flaky runs |
| `test_process_timeout` | `support.run(timeout=)` raises `TimeoutExpired` | tests the standard library through a one-line wrapper | low: drop |
| `test_cleanup_retries_transient_nonempty_directory` | the `ENOTEMPTY` retry seen in CI | none | keep |

### test_screen.py

All nine protect the parser E2E and the action cases read the screen
with, and each covers a case the flake history named: exact names, the
wrong pane, blank status, ANSI and the hover glyph, pane boundaries, cell
widths, whole borders, wrapped boxes, titles from the top border. One
exception: `test_current_rows_require_three_panes` covers
`screen.current_rows`, which nothing else calls. Low: drop the test with
the function. `screen.DECORATIONS` is an empty translation table, so the
`translate` calls are no-ops; the hover glyph is handled by `endswith`.

### test_manual.py

| Test | Protects | Overlap | Verdict |
| --- | --- | --- | --- |
| `test_automatic_checks_never_supply_visual_verdict` | checks never fill in the visual verdict; `next` waits for it | none | keep |
| `test_theme_switching_preserves_readable_modes_and_git_context` | `manual-theme.toml`'s mode colors survive the custom and base theme writes, with the git section when asked | guide `assert_mode_colors` | low: tests fixture data |
| `test_internal_state_mismatch_cannot_be_overridden_by_visual_pass` | a diagnostic FAIL beats a visual PASS | `test_accept_stays_when_file_or_state_checks_fail` | keep one of the two |
| `test_accept_saves_pass_and_advances_without_answering_the_next_step` | `P` saves, advances, leaves the next step unanswered; a stale repeat changes nothing | the stale part repeats twice below | keep |
| `test_accept_stays_when_file_or_state_checks_fail` | failed checks keep the step and say so | the row two above | merge |
| `test_accept_preserves_verdict_if_preparing_next_step_fails` | PASS survives a failed preparation; the error is recorded and a retry works | `..._cli_failure_preserves_existing_results`, `..._history_retains_fixtures...` | keep |
| `test_case_preparation_cli_failure_preserves_existing_results` | seven operations leave saved results alone when a new case cannot be built | `..._failure_preserves_the_previous_attempt` | keep |
| `test_preparation_error_history_retains_fixtures_without_changing_verdicts` | preparation history shows in details and keeps fixtures after a clean exit | the two rows above, `..._completed_details...` | merge into the accept row |
| `test_retained_preparation_diagnostics_do_not_corrupt_json_or_saved_pass` | `KEEP_FIXTURE=1` diagnostics go to stderr, stdout stays JSON | guide `backend_diagnostics`, which runs the real CLI | keep one level |
| `test_case_preparation_failure_preserves_the_previous_attempt` | `start_case` leaves `attempts` alone on failure | `..._cli_failure_preserves_existing_results` | drop: subsumed |
| `test_theme_reload_requires_the_same_acquisition_epoch` | `check` compares the epoch for theme steps | guide `resumed_theme` | keep, it is direct and cheap |
| `test_completed_details_show_results_instead_of_old_instructions` | the details viewer after completion | guide `test()` checks the same screen | low: cheap duplicate |
| `test_failed_auto_check_still_requires_visual_verdict` | `next` does not advance after a failed check | the first row, same assertion with a passing check | low: drop |
| `test_stale_request_leaves_progress_untouched` | a stale token raises and writes nothing | the accept row and the next row | merge |
| `test_stale_cli_request_returns_latest_view_without_changing_results` | the CLI answers a stale token with the current view, for three statuses | none at the CLI level | keep |
| `test_declining_apply_is_verified_from_files` | `check` reads a file expectation | the only unit test where a file check fails | keep |
| `test_skipped_step_records_reason` | `W/s` records SKIP with a note | `..._check_preserves_skip...` starts the same way | keep, cheap |
| `test_skip_next_does_not_check_or_answer_the_following_step` | `S` records SKIP without checks and advances; stale repeat changes nothing | none | keep |
| `test_skip_next_preserves_skip_when_preparing_next_step_fails` | SKIP survives a failed preparation | the accept variant | keep |
| `test_skip_next_finishes_the_last_case_without_recording_pass` | `S` on the last step finishes with SKIP | none | keep |
| `test_check_preserves_skip_but_does_not_hide_failed_diagnostics` | 2026-10-04 defect | none | keep |
| `test_last_step_skip_survives_details_check_and_case_change` | 2026-10-04 defect | none | keep |
| `test_case_change_preserves_unverified_and_error_results` | 2026-10-04 defect | none | keep |
| `test_relative_git_plugin_survives_backend_cwd_change` | the git plugin path is resolved before it is saved | guide `backend_paths`, the same through real processes | keep one level |
| `test_notify_timeout_reaches_every_case_only_when_given` | the walk's `notify_timeout` reaches restarted cases, 0 included | none | keep |
| `test_finished_walk_reopens_on_restart_or_jump` | a finished walk reopens | guide `test()` | keep, cheap |
| `test_lua_serializer_handles_nested_case_arrays` | `support.lua` on nested tables | `test_support.test_lua_string_roundtrip` | move to `test_support.py` |
| `test_failed_attempt_retained_even_after_clean_exit_choice` | `finalize` keeps fixtures after a FAIL | none | keep |
| `test_launcher_waits_for_interrupted_child_before_archiving` | SIGINT to the launcher waits for Yazi before archiving | none; the guide interrupts the editor, not the launcher | keep |
| `test_launcher_rejects_an_old_or_reordered_catalog_without_changing_saved_progress` | an old or reordered case list is refused before any write | none | keep |
| `test_launcher_rejects_changed_or_missing_execution_info_without_writes` | nine metadata mismatches are refused before any write | guide `resume_execution_guard`, four of them through a real process | keep one level |
| `test_harness_error_retains_fixtures_and_is_archived` | a legacy error marker marks ERROR, keeps fixtures and is archived | the next three rows | keep |
| `test_harness_error_is_attributed_to_source_attempt_after_jump` | a marker's token names its origin | `..._multiple_guide_errors...` does the same with two markers | merge |
| `test_multiple_guide_errors_preserve_origin_results_and_complete_history` | 2026-10-11 defect: the journal keeps every error | none | keep |
| `test_imported_guide_error_does_not_override_successful_recheck` | 2026-10-11 defect | none | keep |
| `test_backend_exception_updates_passing_case_and_saved_report` | 2026-10-11 defect | none | keep |
| `test_old_harness_error_preserves_latest_retry_result_after_case_change` | 2026-10-11 defect, five statuses | none | keep |
| `test_invalid_error_token_falls_back_to_current_step` | seven malformed tokens | none | keep |
| `test_successful_cleanup_happens_after_archiving` | archive first, then remove | none | keep |

### test_readme.py

`test_reads_the_readme_itself` keeps the README's four configuration
blocks readable and the flavor named, and is worth keeping. The other
twelve test the block parser of a tool run by hand before a screenshot:
headings, subheadings, a missing, repeated or ill-formed block, the
`show_hidden` addition, the flavor slots. They are cheap and correct, and
protect the parsing half of a tool nothing else calls. Policy: keep them
if the tool stays; they are the first to go when `test/readme.py` is
simplified.

### test_skills.py, test_githooks.py, test_format_hook.py and test_all.py

Nineteen tests, 360 lines, 1.8 s, protecting the repository's own
workflow: the skill symlinks Claude Code needs, the hooks that refuse
`main`, the Lua format hook, and the runner that prints suites whole.
None touches the plugin. `test_skills.test_repository` is a
repository-consistency check and earns its place in `test/check.py`; the
other two in that file test the checker. `test_all.py`'s ordering test
holds 1.1 s of the 4.5 s the unit tests take, by its own design. Policy:
keep them as long as the hooks, the runner and the Claude Code setup are
kept, and let them go with those; judge them as tooling, not as plugin
coverage.

## Yazi-driven suites

### test/runtime.py

| Case | Time | Protects | Overlap |
| --- | --- | --- | --- |
| `status` | 13 s | records for every baseline state, templates and encryption with a missing identity, newline names through the fallback, broken templates and `partial`, navigation and tabs through the probe, failed membership, externally added and forgotten entries, generation cancellation, no polling, the four `process.run` child tests, flavor fallback and theme reload with the epoch kept, git.yazi with `--git-plugin` | the screen checks are substrings (`"CMM" in screen`); `test/e2e.py`'s four status scenarios read exact rows |
| `commands` | 7 s | add, re-add, the menu, forget, destroy, apply refused and accepted, a native conflict, a failed diff | identical code in `test/e2e.py`, which CI runs |
| `command-edges` | 18 s | special names, mixed selections, directory edit, nonrecursive add and destroy, replaced source directories, an outside symlink, templates, encryption, the editor, `[diff].exclude` versus the apply preview, Ctrl-C, a partial editor failure | identical code in `test/e2e.py`; runtime adds the no-destroy-call checks and probe waits |
| `action-coordination` | 5 s | an obsolete pass drains before an action, no subprocess under the lock, the menu's snapshot, cross-directory selection | none; needs the probe and `ya emit-to` |
| `confirmation-pages` | 6 s | every long path on the pages at two sizes, the resize restart, the too-small pane | identical code in `test/e2e.py` |
| `source-ancestor` | 9 s | destroy of a directory holding the source, four ways | identical code in `test/e2e.py`; runtime adds the no-destroy-call check |
| `visual-selection` | 5 s | visual select and unset ranges reach the snapshot | identical code in `test/e2e.py` |

The `check_calls` at the end of each case is the only place
`support.check_call` runs on real calls: 505 calls in one full run,
according to `docs/validation.md`.

### test/e2e.py

| Scenario | Time | Protects | Overlap |
| --- | --- | --- | --- |
| `status-refresh` | 1 s | exact rows for eight baseline states, the refresh, no script run; the CI smoke | the runtime `status` case, by substring |
| `navigation` | 1 s | rows after entering, returning, a new tab and a tab switch | the runtime `status` case, by probe |
| `failure-recovery` | 1 s | `C!!` and recovery | the runtime `status` case |
| `theme-reload` | 0.4 s | wide signs, equal cell widths, an RGB color | the runtime `status` case; the cell-width check is this scenario's own |
| `commands` | 5 s | as runtime `commands`; the CI smoke | identical code |
| `command-edges` | 14 s | as runtime, minus the no-destroy-call checks | identical code |
| `confirmation-pages` | 5 s | as runtime | identical code |
| `source-ancestor` | 10 s | as runtime, minus the no-destroy-call check | identical code |
| `visual-selection` | 5 s | as runtime | identical code |
| `git-coexistence` | optional | git.yazi's sign before chezmoi's on one row | the runtime `status` case with `--git-plugin` |

The scenarios shared with `test/runtime.py` are the same functions in
`test/action_cases.py`. What the E2E run adds is the environment: no
command wrapper, no probe, the real chezmoi streaming its output. What it
loses are the wrapper's call checks and the probe's waits for the action
lock, which E2E replaces with the 0.1-second key settle. E1, E2 and E5
failed in both suites at the same line.

### test/manual_runtime.py

| Function | Time | Protects | Overlap |
| --- | --- | --- | --- |
| `backend_paths` | 0.7 s | the git plugin path through real backend processes | `test_manual.test_relative_git_plugin_survives_backend_cwd_change` |
| `backend_diagnostics` | 0.3 s | preparation failures through the real CLI, with and without `KEEP_FIXTURE` | `test_manual.test_retained_preparation_diagnostics...` |
| `resume_execution_guard` | 0.5 s | four metadata mismatches through a real launcher process | `test_manual.test_launcher_rejects_changed_or_missing_execution_info...`, which covers nine |
| `test` | 72 s | one function: terminal light and dark reports and the fixture theme's colors; `P` and `S` guards; wrapping at 80 columns; restart; hide, compact and full layouts; jump; the details viewer; completion and reopening; then every command case of the walk through the guide's keys; a real preparation failure; the finish menu | the command flows repeat `commands` and `command-edges`; its own are the guide controls, the execution screen's `Running (argv):` with `--apply=false --watch=false`, the `actions.jsonl` history, `partial` cleared after repair (E4), and the fixture-theme colors, which test the fixture and Yazi |
| `foreground_launcher` | 12 s | the executable `test/manual.py` under tmux, Ctrl-C in the editor twice, archive and cleanup | none |
| `resumed_theme` | 4 s | `test/manual.py open` at both theme steps replaces the stale epoch | `test_manual.test_theme_reload_requires_the_same_acquisition_epoch` for the comparison alone |

Two of `test`'s waits are met before the plugin answers: `"Not managed"`
by the Rejections instruction text (E1), and `"Re-add"` in the Add case by
the case title `4/12 Add, Re-add, template and encryption`, so the `r`
after it can be sent before the menu opens; the direct `r` binding then
runs the same re-add, and the step passes either way.

## Duplicates

1. `test/e2e.py` runs `command-edges`, `confirmation-pages`,
   `source-ancestor` and `visual-selection` with the very functions
   `test/runtime.py` runs, with fewer assertions, 34 s of its 42 s. CI
   runs neither; only `commands` and `status-refresh` are the smoke.
2. `test/manual_runtime.py`'s `test` drives add, re-add, template and
   encrypted add, forget, destroy, diff, apply, plain and apply edit,
   Ctrl-C, mixed and directory rejections, shallow destroy, the source
   ancestor, cross-directory and long-target confirmations, a third time
   after the two suites above, as the vehicle for the guide's checks.
3. Three guide behaviors are tested both as unit tests and as real
   processes: the git plugin path, preparation diagnostics and the resume
   guard. One level each would do; the unit tests are broader and
   cheaper, the real ones show the executable path.
4. Within `test_manual.py`: the stale-token rule is asserted in four
   tests, preparation failure in six, error-marker import in six, and
   "a failed check beats a visual PASS" in two.
5. The four status scenarios of `test/e2e.py` repeat the runtime `status`
   case through the screen. They cost 3.5 s together and read exact rows
   where the runtime case reads substrings, so they are complements more
   than copies.
6. `test/actions.lua` line 183 and `support.check_call` both refuse
   `--force`; `test/core.lua` line 201 and `check_call` both pin the
   status filters. The pure checks run on fakes, `check_call` on the real
   calls, so both have a reason; the pure ones cannot fail today.

## Divergence from the plugin's real paths

1. **Timing constants.** Every fixture sets `timeout=1`, `cache_ttl=0.2`,
   `error_backoff=0.5` and `notify_timeout=2`; the defaults of 10, 2, 10
   and 7 run only for people. The reuse window, the backoff that
   `enqueue` applies through `retry_at`, and the 30-second dedupe of the
   status warning have no assertion anywhere; their mutants survive the
   pure suites and E3 passed the runtime `status` case.
2. **The command wrapper.** `test/runtime.py` runs chezmoi through
   `test/command.py`, which captures a query's whole output and writes it
   at exit, so the plugin's line-by-line `read_line_with` loop sees
   streaming output only in `test/e2e.py` and in the `check_process`
   children; and `start_kill` reaches the wrapper, not chezmoi, which no
   fixture lets matter since queries finish well inside their second.
3. **Stubbed Yazi in `test/main.lua`.** `ya.time` is always 0, `ya.emit`
   does nothing, `render.theme` is empty and nothing is hovered, so the
   suite reaches `setup` and the notification paths and no further;
   `take`, `publish`, the worker loop and `interaction.run` run only under
   Yazi.
4. **Fakes that share code with what they test.** `test/core.lua`'s fake
   `status` decides coverage with `core.inside` itself, and
   `test/actions.lua`'s fake `run` is what makes the exact query strings
   fail; both are kept honest by the direct assertions on `inside` and on
   the query list.
5. **Messages checked as `nil`.** The pure suites check that a rejection
   happens, not what it says. Of the plugin's user-facing strings, these
   are pinned by no test at all: the rejections for a non-local path, a
   target outside the destination, a source-tree target, a vanished
   target, a special file and a non-editable entry; `remove is
   unavailable`; `Unsupported option`; the `setup()` reminder; `Command
   completed`, `Command failed or was interrupted`, `Status unavailable`,
   `Action could not finish` and `Could not start or wait for chezmoi`;
   every `effect` line but apply's; the `[including descendants]` and
   `[directory only]` suffixes; and `setup`'s errors other than
   `notify_timeout`'s. The strings the Yazi-driven suites pin are those
   their waits name: `Not managed by chezmoi` (E1), `Select files inside`,
   `Non-recursive destroy`, `contains the source directory`, `Enlarge the
   current pane`, `Pane resized`, `Press Enter to return to Yazi`,
   `chezmoi exited with code`, `Targets:`, `Continue?`, `Add options`,
   `Re-add` and, in the guide alone, `Running (argv):`.
6. **The oracle's blind spot.** `support.check_call` lets any `managed`
   query carry any of the three filter pairs, since a recorded call does
   not say which query it was; only `test/actions.lua`'s `facts` cases
   pin which query gets which pair.
7. **Lua versions.** CI runs `test/core.lua` and `test/actions.lua` under
   Lua 5.1 and 5.4 and `test/main.lua` under neither; Yazi embeds 5.5.1.
8. **Waits that cannot fail.** The two guide waits named above, and the
   negative checks that sleep a fixed time, 0.7 s for no polling and
   0.25 s for no subprocess under the lock, which the verify skill
   already warns can pass under load without seeing anything.
9. **Tests of the fixture.** `assert_mode_colors` and
   `test_theme_switching_preserves_readable_modes_and_git_context` check
   that Yazi draws `test/manual-theme.toml`, a file that exists for the
   walk's readability; the light and dark reports check Yazi's own
   detection.

## Low-value tests

Ranked by what dropping or merging them would save against what they
could still catch. Each is a proposal.

| Rank | Test | Why | Saves | Proposal |
| --- | --- | --- | --- | --- |
| 1 | `test/e2e.py` default scenarios `command-edges`, `confirmation-pages`, `source-ancestor`, `visual-selection` | the same functions as `test/runtime.py` with fewer assertions; E1, E2 and E5 failed in both at the same line; only the missing wrapper is new | 34 s of every full E2E run | take them out of `DEFAULT_CASES`, keep them for `--case`, or run them in CI only, where the runtime suite does not run |
| 2 | `test/manual_runtime.py` `backend_paths`, `backend_diagnostics`, `resume_execution_guard` | each repeats a broader unit test through a real process | 1.5 s, three functions | keep the unit tests; keep one real-process check if the executable path matters |
| 3 | `test_manual.test_failed_auto_check_still_requires_visual_verdict` | the same `next` assertion as `test_automatic_checks_never_supply_visual_verdict` | 4 lines | drop |
| 4 | `test_manual.test_case_preparation_failure_preserves_the_previous_attempt` | `test_case_preparation_cli_failure_preserves_existing_results` asserts the same through the CLI | 7 lines | drop |
| 5 | `test_manual.test_stale_request_leaves_progress_untouched`, `..._accept_stays_when_file_or_state_checks_fail`, `..._preparation_error_history_retains_fixtures...`, `..._harness_error_is_attributed_to_source_attempt_after_jump` | each asserts what a neighbor also asserts | 60 lines | merge into the neighbor named in the table |
| 6 | `test_support.test_process_timeout` | tests `subprocess.run`'s timeout through a one-line wrapper | 3 lines | drop |
| 7 | `test_screen.test_current_rows_require_three_panes` | covers a function nothing calls | 3 lines and 8 of `screen.py` | drop with `current_rows` |
| 8 | `test/actions.lua` lines 155 and 183 (no query flags, no `--force`) and `test/core.lua` lines 157 and 160 (no empty query, no query without targets) | cannot fail against the code as it is; `check_call` repeats the `--force` and filter guards on real calls | 30 lines | keep as one-line tripwires or drop; they add nothing to the mutation score |
| 9 | `test/manual_runtime.py` `assert_mode_colors` and the light and dark reports; `test_manual.test_theme_switching_preserves_readable_modes_and_git_context` | they check the fixture theme and Yazi, not the plugin or the guide's logic | 2 s, 25 lines | keep one assertion that the theme loads, or drop |
| 10 | `test_manual.test_completed_details_show_results_instead_of_old_instructions`, `..._finished_walk_reopens_on_restart_or_jump` | the guide suite checks the same screens | 20 lines | keep, cheap; drop if the guide suite's checks are kept |
| 11 | `test_readme.py`, twelve of thirteen | parser edge cases of a hand-run tool | 70 lines | keep a few that name a refusal; drop the rest when the tool is simplified |
| 12 | `test_githooks.py`, `test_format_hook.py`, `test_skills.py` (two of three), `test_all.py` | tooling, not plugin coverage; `test_all.py`'s ordering test is 1.1 s by design | 1.8 s, 360 lines | a policy call: they go with the tooling they protect |
| 13 | `test_support.test_binary_text_roundtrip`, `test_manual.test_lua_serializer_handles_nested_case_arrays` | one-line wrappers; the serializer test sits in the wrong file | 8 lines | drop the first; move the second to `test_support.py` |
| 14 | `test/actions.lua` lines 48 and 57, `test/core.lua` line 51 | the same kills as their neighbors | 10 lines | keep as documentation, or drop |
| 15 | `test/benchmark.py` | a measurement that asserts only line counts | 1 s | keep as a measurement; do not count it as coverage |

Nothing in `test/runtime.py`'s `status` and `action-coordination` cases,
`test/core.lua`'s and `test/actions.lua`'s parsing and policy blocks,
`test_screen.py`, `test_support.py`'s `check_call`, `stop` and `owned`
tests, or the guide suite's `foreground_launcher` and `resumed_theme` is
low value: each holds assertions no other test makes.

## Gaps noticed on the way

Not what was asked, but what the same evidence shows:

- `--template`, `--encrypt` and apply's `--include=all --exclude=none` are
  pinned only by the Yazi-driven suites (E2, E5); one argv assertion each
  in `test/actions.lua` would catch them in `test/check.py`.
- `partial` is asserted only when it must be true; E4 shows the false
  case rests on the guide suite alone.
- `render.lua` has no pure coverage, and no suite asserts the `partial`
  underline or the `stale` style on screen.
- The chunk arithmetic in `core.chunks` and the halving in recovery
  survive the pure suite's operator mutations.
- `test/main.lua` does not run under Lua 5.1 and 5.4 in CI.

## Limits of this ledger

One run of each suite, on one Linux container, on Lua 5.4 for the pure
suites. The mutation operators are a fixed small set, so a site with no
unique kills may protect against a change they cannot make; the string
and template pins are the clearest case. Verdicts on the harness tests
come from reading `test/manual_backend.py` against each test, not from
mutating it. No human walk, no macOS run and no `--git-plugin` run was
made for this ledger.
