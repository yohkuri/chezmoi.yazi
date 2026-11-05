# Test ledger

Every test in this repository, what it protects, where tests repeat each
other or depart from the paths the plugin really takes, and which ones are
worth little. Measured on 2026-11-05 on the checkout at `a52116c`; the
numbers below are from that run, and the verdicts are a reading of the
code against them. The verdicts were proposals; the three tiers of
[Low-value tests](#low-value-tests) were applied the same day, as that
section records, and the inventory and the tables below describe the
tree after that.

## How the ledger was measured

Everything ran on Ubuntu 24.04 in a container with 4 cores: Yazi 26.9.1
and chezmoi 2.72.2 from the release binaries `check.yml` pins, tmux 3.4,
Lua 5.4.6 (`lua5.4`, since no Lua 5.5 package was at hand; `test/check.py`
runs the pure suites with the Lua 5.5.1 that `mise.toml` pins), uv 0.11.32
and Python 3.14.6. This is the first recorded run of the full runtime, E2E
and guide suites on Linux; CI runs only `test/e2e.py --smoke` there. One run
each, in this order, before the Tier 1 removals, every one passing and
leaving no fixture or Yazi:

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
| `test/test_support.py` | Python unit, 7 tests | harness helpers: Lua serializer, `owned`, `stop`, `da1.answer`, `check_call`, cleanup retry | `test/check.py`, CI | 2.6 s |
| `test/test_screen.py` | Python unit, 8 tests | `test/screen.py`, the parser E2E and the action cases read the screen with | `test/check.py`, CI | 0.01 s |
| `test/test_manual.py` | Python unit, 30 tests | `test/manual_backend.py` and `test/manual.py`: the guide's state machine, archive and launcher | `test/check.py`, CI | 0.3 s |
| `test/test_readme.py` | Python unit, 6 tests | `test/readme.py`'s reading of the README's blocks | `test/check.py`, CI | 0.01 s |
| `test/test_skills.py` | Python unit, 1 test | the symlinks from `.claude/skills` to `.agents/skills` in this checkout | `test/check.py`, CI | 0.02 s |
| `test/runtime.py` | Yazi in tmux, probe and command wrapper, 7 cases | the plugin's records, calls, rendering and actions | by hand | 62 s |
| `test/e2e.py` | Yazi in tmux, screen only, 5 default scenarios, 4 more by `--case`, plus `git-coexistence` | rendering and actions as a user sees them | `--smoke` in CI; the rest by hand | 8 s; 34 s for the four by `--case` |
| `test/manual_runtime.py` | Yazi in tmux, 4 functions | the guide that `test/manual.py` runs, and the plugin flows it drives | by hand | 89 s |
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
| `test_lua_string_roundtrip` | `support.lua` writes fixture values Lua reads back byte for byte; needs `lua` on `PATH` | the next row | keep |
| `test_lua_serializer_handles_nested_arrays` | `support.lua` on nested tables; moved from `test_manual.py` as Tier 2 | the row above | keep |
| `test_owned_marker_and_symlink` | the fixture-ownership guards and `stop`'s socket check | none | keep, it guards deletion |
| `test_da1_counts_each_query_once_across_reads` | `da1.answer` over every chunk size | none | keep |
| `test_check_call` | the call oracle, with 14 ways past an earlier version | none | keep |
| `test_stop_kills_only_what_outlives_the_server` | leftover Yazi after the tmux server stops; 2.4 s, needs tmux | none | keep; the slowest unit test, for the leftover Yazi found behind weeks of flaky runs |
| `test_cleanup_retries_transient_nonempty_directory` | the `ENOTEMPTY` retry seen in CI | none | keep |

`test_binary_text_roundtrip`, which checked two one-line wrappers, and
`test_process_timeout`, which checked the standard library's timeout
through one, were removed as Tier 1.

### test_screen.py

All eight protect the parser E2E and the action cases read the screen
with, and each covers a case the flake history named: exact names, the
wrong pane, blank status, ANSI and the hover glyph, cell widths, whole
borders, wrapped boxes, titles from the top border.
`test_current_rows_require_three_panes`, which covered
`screen.current_rows`, a function nothing called, was removed with it as
Tier 1. `screen.DECORATIONS` is an empty translation table, so the
`translate` calls are no-ops; the hover glyph is handled by `endswith`.

### test_manual.py

| Test | Protects | Overlap | Verdict |
| --- | --- | --- | --- |
| `test_automatic_checks_never_supply_visual_verdict` | checks never fill in the visual verdict; `next` waits for it | none | keep |
| `test_internal_state_mismatch_cannot_be_overridden_by_visual_pass` | a diagnostic FAIL beats a visual PASS, and accepting with it keeps the step and says so | none | keep |
| `test_accept_saves_pass_and_advances_without_answering_the_next_step` | `P` saves, advances, leaves the next step unanswered; a stale repeat changes nothing | `test_stale_cli_request...`, at the CLI level | keep |
| `test_accept_preserves_verdict_if_preparing_next_step_fails` | PASS survives a failed preparation; the error is recorded, shows in details, leaves the error journal alone, a retry works, and the history alone retains the fixtures | `..._cli_failure_preserves_existing_results` | keep |
| `test_case_preparation_cli_failure_preserves_existing_results` | seven operations leave saved results alone when a new case cannot be built | none | keep |
| `test_retained_preparation_diagnostics_do_not_corrupt_json_or_saved_pass` | `KEEP_FIXTURE=1` diagnostics go to stderr, stdout stays JSON | guide `backend_diagnostics`, the one real-process check kept | keep |
| `test_theme_reload_requires_the_same_acquisition_epoch` | `check` compares the epoch for theme steps | guide `resumed_theme` | keep, it is direct and cheap |
| `test_completed_details_show_results_instead_of_old_instructions` | the details viewer after completion | none: the guide suite checks the guide panel after completion, not the viewer | keep |
| `test_stale_cli_request_returns_latest_view_without_changing_results` | the CLI answers a stale token with the current view, for three statuses | none at the CLI level | keep |
| `test_declining_apply_is_verified_from_files` | `check` reads a file expectation | the only unit test where a file check fails | keep |
| `test_skipped_step_records_reason` | `W/s` records SKIP with a note | `..._check_preserves_skip...` starts the same way | keep, cheap |
| `test_skip_next_does_not_check_or_answer_the_following_step` | `S` records SKIP without checks and advances; stale repeat changes nothing | none | keep |
| `test_skip_next_preserves_skip_when_preparing_next_step_fails` | SKIP survives a failed preparation | the accept variant | keep |
| `test_skip_next_finishes_the_last_case_without_recording_pass` | `S` on the last step finishes with SKIP | none | keep |
| `test_check_preserves_skip_but_does_not_hide_failed_diagnostics` | 2026-10-04 defect | none | keep |
| `test_last_step_skip_survives_details_check_and_case_change` | 2026-10-04 defect | none | keep |
| `test_case_change_preserves_unverified_and_error_results` | 2026-10-04 defect | none | keep |
| `test_relative_git_plugin_survives_backend_cwd_change` | the git plugin path is resolved before it is saved | none since Tier 2 removed the guide's `backend_paths` | keep |
| `test_notify_timeout_reaches_every_case_only_when_given` | the walk's `notify_timeout` reaches restarted cases, 0 included | none | keep |
| `test_failed_attempt_retained_even_after_clean_exit_choice` | `finalize` keeps fixtures after a FAIL | none | keep |
| `test_launcher_waits_for_interrupted_child_before_archiving` | SIGINT to the launcher waits for Yazi before archiving | none; the guide interrupts the editor, not the launcher | keep |
| `test_launcher_rejects_an_old_or_reordered_catalog_without_changing_saved_progress` | an old or reordered case list is refused before any write | none | keep |
| `test_launcher_rejects_changed_or_missing_execution_info_without_writes` | nine metadata mismatches are refused before any write | none since Tier 2 removed the guide's `resume_execution_guard` | keep |
| `test_harness_error_retains_fixtures_and_is_archived` | a legacy error marker marks ERROR, keeps fixtures and is archived | the next two rows | keep |
| `test_multiple_guide_errors_preserve_origin_results_and_complete_history` | 2026-10-11 defect: the journal keeps every error, and each marker lands on its own attempt and step | none | keep |
| `test_imported_guide_error_does_not_override_successful_recheck` | 2026-10-11 defect | none | keep |
| `test_backend_exception_updates_passing_case_and_saved_report` | 2026-10-11 defect | none | keep |
| `test_old_harness_error_preserves_latest_retry_result_after_case_change` | 2026-10-11 defect, five statuses | none | keep |
| `test_invalid_error_token_falls_back_to_current_step` | seven malformed tokens | none | keep |
| `test_successful_cleanup_happens_after_archiving` | archive first, then remove | none | keep |

Removed as Tier 1: `test_failed_auto_check_still_requires_visual_verdict`,
which made the first row's `next` assertion again after a failed check,
and `test_case_preparation_failure_preserves_the_previous_attempt`, which
`test_case_preparation_cli_failure_preserves_existing_results` subsumes.
Tier 2 merged `test_accept_stays_when_file_or_state_checks_fail`,
`test_preparation_error_history_retains_fixtures_without_changing_verdicts`
and `test_harness_error_is_attributed_to_source_attempt_after_jump` into
the rows above that now describe them, removed
`test_stale_request_leaves_progress_untouched`, whose assertion the accept
row already made, `test_finished_walk_reopens_on_restart_or_jump`, which the
guide suite covers by restart and by jump, and
`test_theme_switching_preserves_readable_modes_and_git_context`, which
tested the fixture theme, and moved the serializer test to
`test_support.py`.

### test_readme.py

`test_reads_the_readme_itself` keeps the README's four configuration
blocks readable and the flavor named. The five beside it each name a
refusal of the parser of a tool run by hand before a screenshot: a missing
block, a second block for one file, a TOML block that does not parse, a
README without the section, and a `yazi.toml` that already has `[mgr]`.
Tier 3 removed the other seven, which tested the parser's mechanics: a
block kept as it stands, blocks skipped for naming no file or another
file, a heading ending the section and a subheading not, the
`show_hidden` addition, and the flavor slots.

### test_skills.py and the tooling tests

Nineteen tests, 360 lines, 1.8 s, protected the repository's own
workflow: the skill symlinks Claude Code needs, the hooks that refuse
`main`, the Lua format hook, and the runner that prints suites whole.
None touched the plugin. The ledger's policy was to keep them as long as
the tooling they protect is kept; the maintainer chose to remove them
after Tier 3, and `test_githooks.py`, `test_format_hook.py`, `test_all.py`
and the two tests of `test_skills.py` that exercised the link checker on
fixture repositories went. `test_skills.test_repository` stays: it checks
this checkout's own skill links, which `test/check.py` is the place for.
The hooks, the format hook, the checker and `test/all.py` now have no
tests; `docs/validation.md` keeps the hand-run evidence for them.

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
| `command-edges` | 14 s, `--case` only | as runtime, minus the no-destroy-call checks | identical code |
| `confirmation-pages` | 5 s, `--case` only | as runtime | identical code |
| `source-ancestor` | 10 s, `--case` only | as runtime, minus the no-destroy-call check | identical code |
| `visual-selection` | 5 s, `--case` only | as runtime | identical code |
| `git-coexistence` | optional | git.yazi's sign before chezmoi's on one row | the runtime `status` case with `--git-plugin` |

The scenarios shared with `test/runtime.py` are the same functions in
`test/action_cases.py`. What the E2E run adds is the environment: no
command wrapper, no probe, the real chezmoi streaming its output. What it
loses are the wrapper's call checks and the probe's waits for the action
lock, which E2E replaces with the 0.1-second key settle. E1, E2 and E5
failed in both suites at the same line. Since Tier 1, the four shared
scenarios other than `commands` run only when named with `--case`.

### test/manual_runtime.py

| Function | Time | Protects | Overlap |
| --- | --- | --- | --- |
| `backend_diagnostics` | 0.3 s | preparation failures through the real CLI, with and without `KEEP_FIXTURE`; since Tier 2 the one check of the backend through real processes | `test_manual.test_retained_preparation_diagnostics...` |
| `test` | 71 s | one function: one check that the fixture theme loaded; `P` and `S` guards; wrapping at 80 columns; restart; hide, compact and full layouts; jump; the details viewer; completion and reopening; then every command case of the walk through the guide's keys; a real preparation failure; the finish menu | the command flows repeat `commands` and `command-edges`; its own are the guide controls, the execution screen's `Running (argv):` with `--apply=false --watch=false`, the `actions.jsonl` history and `partial` cleared after repair (E4) |
| `foreground_launcher` | 12 s | the executable `test/manual.py` under tmux, Ctrl-C in the editor twice, archive and cleanup | none |
| `resumed_theme` | 4 s | `test/manual.py open` at both theme steps replaces the stale epoch | `test_manual.test_theme_reload_requires_the_same_acquisition_epoch` for the comparison alone |

Two of `test`'s waits are met before the plugin answers: `"Not managed"`
by the Rejections instruction text (E1), and `"Re-add"` in the Add case by
the case title `4/12 Add, Re-add, template and encryption`, so the `r`
after it can be sent before the menu opens; the direct `r` binding then
runs the same re-add, and the step passes either way. Tier 2 removed
`backend_paths` and `resume_execution_guard`, whose unit twins are
broader, and found a third weak wait in `foreground_launcher`: it left
its fixture, and so stopped the tmux server, as soon as the launcher
printed `Results:`, which the launcher prints before it removes its
fixtures. One run killed the launcher mid-removal and the test then
failed its own check that the session was gone. It now waits for tmux's
`Pane is dead` line, which says the launcher has exited.

## Duplicates

1. `test/e2e.py` ran `command-edges`, `confirmation-pages`,
   `source-ancestor` and `visual-selection` by default with the very
   functions `test/runtime.py` runs, with fewer assertions, 34 s of its
   42 s. CI runs neither; only `commands` and `status-refresh` are the
   smoke. Since Tier 1 they run only by `--case`.
2. `test/manual_runtime.py`'s `test` drives add, re-add, template and
   encrypted add, forget, destroy, diff, apply, plain and apply edit,
   Ctrl-C, mixed and directory rejections, shallow destroy, the source
   ancestor, cross-directory and long-target confirmations, a third time
   after the two suites above, as the vehicle for the guide's checks.
3. Three guide behaviors were tested both as unit tests and as real
   processes: the git plugin path, preparation diagnostics and the resume
   guard. The unit tests are broader and cheaper, the real ones show the
   executable path; Tier 2 kept `backend_diagnostics` alone.
4. Within `test_manual.py`, the stale-token rule was asserted in four
   tests, preparation failure in six, error-marker import in six, and
   "a failed check beats a visual PASS" in two, until Tier 2 merged them.
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
8. **Weak waits.** The two guide waits named above; the negative checks
   that sleep a fixed time, 0.7 s for no polling and 0.25 s for no
   subprocess under the lock, which the verify skill already warns can
   pass under load without seeing anything; and two that the tier runs
   caught and fixed: `foreground_launcher` left its fixture as soon as the
   launcher printed `Results:`, before the launcher had removed its own
   fixtures, and `action_cases.finish` matched the previous command's
   exit prompt, which `ui.hide` shows from the main screen until the new
   command clears it, a window the 0.1-second key settle had hidden until
   one runtime run. `finish` now gives a prompt capture equal to the last
   one half a second to change.
9. **Tests of the fixture.** `assert_mode_colors` and
   `test_theme_switching_preserves_readable_modes_and_git_context` checked
   that Yazi draws `test/manual-theme.toml`, a file that exists for the
   walk's readability, and the light and dark reports checked Yazi's own
   detection; since Tier 2 one color check remains, that the theme loaded.

## Low-value tests

Ranked by what dropping or merging them would save against what they
could still catch, in three tiers: the unconditional removals, the merges
and judgment calls, and the policy calls. All three were applied on
2026-11-05, each in its own commit after the ledger's, each row by the
first option its proposal names, except Tier 3's tooling row, which the
maintainer then decided the other way in a commit of its own.

### Tier 1, applied

| Rank | Test | Why | Saved | Done |
| --- | --- | --- | --- | --- |
| 1 | `test/e2e.py` default scenarios `command-edges`, `confirmation-pages`, `source-ancestor`, `visual-selection` | the same functions as `test/runtime.py` with fewer assertions; E1, E2 and E5 failed in both at the same line; only the missing wrapper was new | 34 s of every default E2E run | taken out of `DEFAULT_CASES`; they still run by `--case` |
| 2 | `test_manual.test_failed_auto_check_still_requires_visual_verdict` | the same `next` assertion as `test_automatic_checks_never_supply_visual_verdict` | 4 lines | removed |
| 3 | `test_manual.test_case_preparation_failure_preserves_the_previous_attempt` | `test_case_preparation_cli_failure_preserves_existing_results` asserts the same through the CLI | 7 lines | removed |
| 4 | `test_support.test_process_timeout` | tested `subprocess.run`'s timeout through a one-line wrapper | 3 lines | removed |
| 5 | `test_screen.test_current_rows_require_three_panes` | covered a function nothing called | 3 lines and 8 of `screen.py` | removed with `screen.current_rows` |
| 6 | `test_support.test_binary_text_roundtrip` | two one-line wrappers that cannot fail unless someone adds normalization | 5 lines | removed |

After the removals, on the same container, with lua-language-server
3.19.2, StyLua 2.6.0 and ShellCheck 0.11.0 from their releases and `lua`
still 5.4.6, `test/check.py` passed in full in 8 s: Markdown, LuaLS,
StyLua and ShellCheck clean, 63 core, 126 action policy and 20 main
assertions, and 83 Python tests, five fewer. Then, one run each:
`test/runtime.py` (16 passes) in 63 s, `test/e2e.py` (5 scenarios) in 8 s
against 42 s before, the four scenarios by `--case` in 34 s, and
`test/manual_runtime.py` (15) in 89 s, none killing a process.

### Tier 2, merges and judgment calls, applied

| Rank | Test | Why | Proposal | Done |
| --- | --- | --- | --- | --- |
| 1 | `test/manual_runtime.py` `backend_paths`, `backend_diagnostics`, `resume_execution_guard` | each repeated a broader unit test through a real process | keep the unit tests; keep one real-process check if the executable path matters | `backend_paths` and `resume_execution_guard` removed; `backend_diagnostics` kept, since only a real process shows the stdout and stderr protocol |
| 2 | `test_manual.test_stale_request_leaves_progress_untouched`, `..._accept_stays_when_file_or_state_checks_fail`, `..._preparation_error_history_retains_fixtures...`, `..._harness_error_is_attributed_to_source_attempt_after_jump` | each asserted what a neighbor also asserts | merge into the neighbor named in the table | merged: the accept-stays assertions into `test_internal_state_mismatch...`, the history test into `test_accept_preserves_verdict...`, the attribution into `test_multiple_guide_errors...`; the stale test went, its assertion already in the accept test |
| 3 | `test/actions.lua` lines 155 and 183 (no query flags, no `--force`) and `test/core.lua` lines 157 and 160 (no empty query, no query without targets) | cannot fail against the code as it is; `check_call` repeats the `--force` and filter guards on real calls | keep as one-line tripwires or drop; they add nothing to the mutation score | kept: three are one line already, and the `--force` sweep is the only such guard that CI runs, since `check_call` runs only in local runtime fixtures |
| 4 | `test/manual_runtime.py` `assert_mode_colors` and the light and dark reports; `test_manual.test_theme_switching_preserves_readable_modes_and_git_context` | they checked the fixture theme and Yazi, not the plugin or the guide's logic | keep one assertion that the theme loads, or drop | one `assert_mode_colors` of the normal-mode bar kept; the light and dark reports, the select and unset modes, the two Theme-case checks and the unit test removed |
| 5 | `test_manual.test_completed_details_show_results_instead_of_old_instructions`, `..._finished_walk_reopens_on_restart_or_jump` | the guide suite was thought to check the same screens | keep, cheap; drop if the guide suite's checks are kept | the reopen test removed, since the guide restarts and jumps after completion; the details test kept, since the guide never opens the details viewer after completion, which the row had wrong |
| 6 | `test_manual.test_lua_serializer_handles_nested_case_arrays` | the serializer test sat in the wrong file | move to `test_support.py` | moved, as `test_lua_serializer_handles_nested_arrays` |
| 7 | `test/actions.lua` lines 48 and 57, `test/core.lua` line 51 | the same kills as their neighbors | keep as documentation, or drop | kept as documentation |

After Tier 2, on the same container: `test/check.py` passed in full in 9 s
with 77 Python tests, six fewer; `test/runtime.py` (16 passes) in 64 s and
`test/e2e.py` (5 scenarios) in 7 s. `test/manual_runtime.py` failed its
first run at `foreground_launcher`'s check that the launcher's session
was gone, the race the previous section describes, which the removals
had not touched; with the wait for the launcher's exit added, it passed
alone, 13 passes in 89 s, none killing a process.

### Tier 3, policy, applied

| Rank | Test | Why | Proposal | Done |
| --- | --- | --- | --- | --- |
| 1 | `test_readme.py`, twelve of thirteen | parser edge cases of a hand-run tool | keep a few that name a refusal; drop the rest when the tool is simplified | the five that name a refusal kept with the README self-check; the other seven removed |
| 2 | `test_githooks.py`, `test_format_hook.py`, `test_skills.py` (two of three), `test_all.py` | tooling, not plugin coverage; `test_all.py`'s ordering test is 1.1 s by design | a policy call: they go with the tooling they protect | kept at first, since the tooling stays; then removed at the maintainer's call in the following commit, `test_skills.test_repository` alone staying |
| 3 | `test/benchmark.py` | a measurement that asserts only line counts | keep as a measurement; do not count it as coverage | kept |

After Tier 3, on the same container: `test/check.py` passed in full in 9 s
with 70 Python tests, seven fewer, and `test/e2e.py` (5 scenarios) in 8 s
and `test/manual_runtime.py` (13 passes) in 87 s. `test/runtime.py`
failed its first run in 21 s at the `commands` case's last `finish`, whose
prompt wait matched the previous `apply` screen, the race item 8 of the
divergence section describes; with the half-second grace in `finish`,
every suite passed again in one run each: `test/check.py` in 8 s,
`test/runtime.py` (16 passes) in 65 s, `test/e2e.py` in 9 s and
`test/manual_runtime.py` in 87 s, none killing a process. After the
tooling tests went, one run each again: `test/check.py` in 7 s with 52
Python tests, `test/runtime.py` (16 passes) in 65 s, `test/e2e.py` in 9 s
and `test/manual_runtime.py` (13 passes) in 80 s, none killing a process.

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
mutating it. Each tier's changes were checked by one run of every suite,
recorded above, with a second run of the guide suite for Tier 2 and of
every suite for Tier 3 after the harness race each first run found was
fixed. No human walk, no macOS run and no `--git-plugin` run was made
for this ledger.
