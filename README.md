# chezmoi.yazi

Run scoped chezmoi commands and show management and status in Yazi's linemode.
A managed file gets a
`C` marker and the original two `chezmoi status` columns. Directories also show
whether any managed descendant differs, including missing destination files.

Tested with **Yazi 26.9.1 and chezmoi 2.72.2 on macOS**. The plugin requires
Yazi 26.9.1 or newer and local Unix destination paths. Windows and source-tree
display are unsupported;
other Yazi/chezmoi versions and Linux have not been verified locally.

## Installation

Place this repository at `~/.config/yazi/plugins/chezmoi.yazi` (or under
`$YAZI_CONFIG_HOME/plugins` if configured). For a local checkout, symlink that
directory to the checkout instead. Keep all root Lua files together.

Add to `init.lua`:

```lua
require("chezmoi"):setup()
```

Add to `yazi.toml`:

```toml
[[plugin.prepend_fetchers]]
url = "*"
run = "chezmoi"
group = "chezmoi"

[[plugin.prepend_fetchers]]
url = "*/"
run = "chezmoi"
group = "chezmoi"
```

Add optional menu and manual refresh bindings to `keymap.toml`:

```toml
[[mgr.prepend_keymap]]
on = ["c", "m"]
run = "plugin chezmoi -- menu"
desc = "Chezmoi actions"

[[mgr.prepend_keymap]]
on = ["c", "r"]
run = "plugin chezmoi -- refresh"
desc = "Refresh chezmoi status"
```

The plugin adds a linemode child and preserves the selected linemode. Its
default order is `1600`, after git.yazi's default `1500`. Keep git.yazi's own
setup and fetcher entries when using both plugins.

## Reading the display

The default layout is `MXYD`, preceded by a space. Quotes below make the slots
visible; they are not rendered.

| Display | Meaning |
| --- | --- |
| `"C   "` | Managed, no difference reported |
| `"C M "` | Apply would modify the file |
| `"CMM "` | Local file changed; apply would also change it |
| `"C D "` | Managed removal operation |
| `"C  *"` | Directory has a changed managed descendant |
| `"C!! "` | Managed, but the own-status query failed |
| `"C  !"` | Directory's own status is known; descendant scan failed |
| `"?   "` | Membership not yet known (directory summary also shows `?`) |
| `"!   "` | Membership acquisition failed (directory summary also shows `!`) |
| `"    "` | Unmanaged, with no changed descendants |

`X` compares the last state written by chezmoi with the actual destination.
`Y` describes the change from the actual destination to the target state.
Spaces mean no reported change; `A`, `D`, `M`, and `R` mean added, deleted,
modified, and a pending script respectively (`R` only occurs in Y). A successful
status query may omit a path when actual and target contents already match.

Own status and descendant summary are independent. A directory containing
managed descendants does not receive `C` unless it is managed itself. A `*`
with the `partial` style confirms a difference but indicates that another
descendant failed to evaluate. Missing files contribute to summaries without
adding artificial rows to Yazi.

## Refresh behavior

Queries run asynchronously on fetcher activity and directory navigation.
Requests share one worker; results are reused briefly to avoid duplicate work.
There is **no periodic polling**. External source/template edits while the
view is stationary may require `plugin chezmoi -- refresh`. That command
refreshes
membership and the current file list immediately, invalidating older work.

An automatic refresh can display old results with the `stale` style while
working. Once a query fails, failure signs replace the old status. Manual
refresh and navigation clear old results immediately. Failure notifications
are limited to one per 30 seconds and never include raw stderr or secrets.

## Commands

Use the menu or bind any command directly. Both routes use the same target
validation and confirmation rules. No arguments still means `refresh`.

| Plugin command | Action |
| --- | --- |
| `plugin chezmoi -- menu` | Choose an action; `Add options` offers template, encrypted, or both |
| `plugin chezmoi -- add` | Copy destination files into source state, replacing existing entries |
| `plugin chezmoi -- add --template` | Add as templates |
| `plugin chezmoi -- add --encrypt` | Add encrypted; can be combined with `--template` |
| `plugin chezmoi -- re-add` | Re-add modifications; chezmoi skips templates and non-files |
| `plugin chezmoi -- edit` | Edit source files through chezmoi's configured editor |
| `plugin chezmoi -- edit --apply` | Edit, show diff, confirm, then apply |
| `plugin chezmoi -- diff` | Show diff using chezmoi's configured diff tool/pager |
| `plugin chezmoi -- apply` | Show diff, confirm, then apply |
| `plugin chezmoi -- forget` | Stop managing entries; keep destination files |
| `plugin chezmoi -- destroy` | Permanently delete source and destination entries |
| `plugin chezmoi -- refresh` | Refresh the visible status |

Actions snapshot the active tab's selection, including selected files in other
directories. With no selection, they use the hovered file. Empty targets never
become an unscoped chezmoi command. Remote URLs, targets outside the destination,
source-tree paths, unavailable files, and unsupported file types are rejected.
Fresh managed information is required; known inapplicable targets stop the
whole selection before execution. Edit requires individual files or symlinks,
not directories. External, removal, and script entries cannot be edited,
forgotten, or destroyed through these actions.

Directories include descendants by default. `add`, `re-add`, `diff`, `apply`,
and `destroy` accept `--recursive=false` on direct bindings. For `destroy`,
this option accepts files and symlinks but rejects directories: chezmoi still
deletes a directory's descendants with `--recursive=false`. Recursive parent
targets absorb duplicate child selections. `forget` includes a directory's
source descendants and has no nonrecursive option. Select a managed parent
directory to restore missing descendants with apply. `remove` is unavailable;
choose `forget` or `destroy` explicitly. Other CLI flags are not accepted.

Single-file add/re-add and opening the editor need no plugin confirmation.
Multiple-target or directory add/re-add operations confirm their scope first.
Forget/destroy always confirm their different effects. Confirmations list
targets in pages sized to the current pane, including continuations of long
paths. Cancelling any page cancels execution. A pane resize restarts review
from the first page; panes smaller than 32 columns or 8 rows must be enlarged
before retrying. Chezmoi's own prompts remain enabled; the plugin never adds
`--force`.

Apply always follows a successful diff and explicit confirmation. The preview
and apply use the same targets, recursion, and all entry types, matching a
normal chezmoi apply; scripts are not independently excluded. In particular,
the apply preview overrides `[diff].include`/`exclude`, which affect standalone
diff but do not restrict chezmoi apply. A standalone `diff` retains those
settings. Other chezmoi settings, including secret skipping, are inherited.
The linemode continues to evaluate all types independently of these settings.
Diff is a preview, not a transaction: chezmoi evaluates again at apply time.
Both edit commands explicitly disable chezmoi's `edit.apply` and `edit.watch`
settings. Editing alone cannot apply changes, and `edit --apply` waits for the
plugin's separate diff and confirmation stages.

Yazi temporarily hands over the terminal for the editor, pager, credentials,
and conflict prompts. Press Enter after each command to return or continue.
Interactive commands have no status-query timeout. Only one action runs per
Yazi instance; status queries pause and obsolete results are discarded.
After an executed command, success, failure, and interruption all trigger a
file-list/status refresh. Failures may leave partial changes; there is no
automatic retry or rollback. Cancelling apply after edit keeps the source edit.
Completion means the command finished, not that every entry was changed.
Raw command output stays in the terminal and is not copied to plugin logs or
notifications. Terminal scrollback remains subject to your terminal settings.

## Configuration

All options are optional:

```lua
require("chezmoi"):setup {
  order = 1600,
  directory_summary = true,
  command = "chezmoi",
  timeout = 10,                  -- seconds per subprocess
  cache_ttl = 2,                 -- reuse window, not a polling interval
  error_backoff = 10,            -- automatic retry delay after incomplete work
  max_retries = 8,               -- extra status queries per acquisition pass
  argument_bytes = 8192,         -- target argument budget per initial batch
  output_limit = 16 * 1024 * 1024,
  -- config = "/absolute/path/chezmoi.toml",
  -- source = "/absolute/path/source",
  -- destination = "/absolute/path/destination",
  -- persistent_state = "/absolute/path/chezmoi.db",
  -- cache = "/absolute/path/cache",
}
```

By default chezmoi resolves its usual configuration and destination. Optional
context paths are passed consistently to every command. `command` is one
executable name/path, not a shell expression. Disabling `directory_summary`
omits the fourth slot and avoids evaluating descendants for summary purposes.

Large directories can cover most of the managed tree. Smaller timeouts or a
lower retry budget trade completeness for latency; failed coverage remains
explicit. Each acquisition pass refreshes the managed index, so new and
forgotten entries and dynamically generated removals can be discovered.

## Theme and flavor

Add any of these keys to `[chezmoi]` in `theme.toml` or a flavor's `flavor.toml`:

```toml
[chezmoi]
managed   = { fg = "cyan" }
unmanaged = { fg = "darkgray" }
clean     = { fg = "green" }
added     = { fg = "green" }
modified  = { fg = "yellow" }
deleted   = { fg = "red" }
run       = { fg = "magenta" }
changed   = { fg = "yellow" }
unknown   = { fg = "darkgray" }
error     = { fg = "red" }
partial   = { fg = "yellow", underline = true }
stale     = { fg = "darkgray", dim = true }

managed_sign   = "C"
unmanaged_sign = ""
clean_sign     = " "
added_sign     = "A"
modified_sign  = "M"
deleted_sign   = "D"
run_sign       = "R"
changed_sign   = "*"
unknown_sign   = "?"
error_sign     = "!"
```

Yazi merges the flavor and theme; the theme wins for each specified key. For
example, overriding `modified` replaces that style rather than merging its
individual properties. Unspecified plugin keys use the defaults above. Signs
may be empty or wide; each slot is padded to its largest configured sign's
terminal width. Control characters are rejected. Hovered rows inherit Yazi's
highlight colors.

Theme reload rebuilds styles and widths without querying chezmoi. For Yazi
26.9.1, an optional binding is:

```toml
[[mgr.prepend_keymap]]
on = ["c", "t"]
run = "app:theme"
desc = "Reload theme"
```

## Evaluation and limits

Background status acquisition calls destination discovery, `managed`, and
`status`; it never calls mutation commands. Explicit actions are described
above. Templates and encrypted files are evaluated by
chezmoi, with all entry categories included and secret skipping disabled.
Thus configured `include`/`exclude` preferences for a bare status command are
intentionally overridden. Apply scripts are reported, not executed.

Background queries use argument arrays, closed stdin, `--no-tty`, no pager/color/progress,
and a timeout. Missing credentials or invalid templates produce failure signs.
chezmoi hooks, template functions, decryptors, and external resources may still
run commands, refresh caches, or open their own UI. This is full chezmoi
evaluation, not a sandbox.

The deadline covers reading stdout and waiting for the **direct child**, even
when that child is silent or closes stdout before exiting. Timeout termination
does not guarantee termination of arbitrary grandchildren. The output limit
is checked after each line read; it is not a strict peak-memory limit for one
very large unterminated line. Cancellation takes effect between reads, at
latest after the current command's timeout. A pass may contain multiple
commands, each with its own deadline.

NUL-separated managed paths and validated status coverage prevent failed or
ambiguous output from becoming a false clean result. CR/LF filenames require
individual nonrecursive queries because status has no NUL output format.
Membership and status are separate snapshots; concurrent filesystem changes
can produce a failure until the next refresh.

## Plugin conventions

The layout follows [Yazi's plugin overview][plugin-overview]: `main.lua` is the
entry point, with `README.md` and `LICENSE` at the plugin root. `setup` stores
configuration and render state in the synchronous plugin state; `entry` and
`fetch` perform asynchronous acquisition. Every `ya.sync` block is declared
unconditionally at the top level. Cross-context messages carry plain values
and tables, without moving live file userdata or UI objects between threads.
The leading `@since` annotation enforces the supported Yazi minimum.

[plugin-overview]: https://yazi-rs.github.io/docs/plugins/overview/

## Development

Install Lua 5.5.1, uv 0.11.19, Node.js 24+, LuaLS 3.19.1, and StyLua 2.5.2
using your preferred installer. mise is optional. From the repository root, run:

```sh
npm ci --ignore-scripts
npm run setup:types
test/check.py
```

`npm run check` uses `.markdownlint-cli2.yaml`, `.luarc.json`, and
`.stylua.toml`, then runs the pure Lua status and action suites, Python syntax checks,
and harness unit tests. LuaLS checks the plugin and in-Yazi probes as Lua 5.5.

`mise.toml` only pins tool versions for developers who use mise; it defines
no tasks. If you use mise, `mise trust` and `mise install` install those tools.
The executable Python scripts use uv directly to prepare the locked environment
and run Python, so no separate Python setup command is required.

Lua 5.5.1 and uv 0.11.19 are the pinned versions. Lua matches the Yazi 26.9.1 build:
its `lua55` feature and locked `lua-src` 551.0.1 embed Lua 5.5.1. The independent
Lua executable is for unit tests; it does not replace Yazi's embedded runtime.
uv selects Python 3.14 via `.python-version` and maintains `.venv` and `uv.lock`.
The Python harness uses only the standard library; no pip installation is used.

Yazi types are downloaded to ignored `.dev/types` at a fixed revision with a
SHA-256 check. `types/compat.lua` supplies missing runtime declarations and the
plugin theme extension. No personal Yazi configuration is required.
JavaScript tools are locked in `package-lock.json`; the `smol-toml` override
selects its security fix. None of these tools is a plugin runtime dependency.

Validate the commits that a pull request will introduce:

```sh
npm run lint:commits -- origin/main HEAD
# Before the first commit, validate a prospective message instead:
npm run lint:commits -- --file /absolute/path/to/message.txt
```

This uses `.commitlintrc.yml` and checks the entire message for ASCII English,
including bodies and footers. ASCII makes header length equal display columns
and excludes emojis. Subject length above 50 is a warning; header length above
72 is an error. GitHub Actions checks PR commits and pushed commit ranges,
including all commits on a newly created branch. It also runs `npm run check`
and Lua 5.5.1 syntax and Lua 5.1/5.4 compatibility checks. A separate Ubuntu
job runs the black-box E2E smoke scenario with pinned Yazi and chezmoi release
binaries. No Git hooks are installed automatically.

Run `test/check.py` for development checks, `test/runtime.py` for integration
tests with an internal probe, `test/e2e.py` for black-box terminal tests,
`test/manual.py` for an interactive fixture, or `test/benchmark.py` for
acquisition measurements. Run these commands from the repository root with
the required tools on `PATH`; none invokes mise.

Start an interactive fixture with `test/manual.py`. The command starts Yazi
directly in your terminal; no attach command or tmux is needed. For expected
displays and step-by-step checks, see the
[manual acceptance checklist](test/MANUAL.md).

Run the isolated integration suite separately:

```sh
test/runtime.py
```

The runtime test needs Yazi, chezmoi, tmux, and the uv-managed Python. It
creates isolated source/destination/config/state/cache directories and a
private tmux socket; it never applies the user's dotfiles or edits their Yazi
configuration. It checks actual rendered terminal output as well as plugin
records.

Run the complete black-box E2E suite, or its shorter CI smoke scenario:

```sh
test/e2e.py
test/e2e.py --smoke
# Optional, using an existing git.yazi checkout:
test/e2e.py --git-plugin /absolute/path/to/git.yazi
```

The E2E suite starts a fresh isolated Yazi for each scenario and checks visible
terminal output, process exit state, and fixture files. It invokes the real chezmoi
binary directly, without the runtime suite's probe or command wrapper. Use
`--case NAME` to isolate one scenario, `--keep` to retain fixtures, or
`--artifacts DIR` to save failure captures and logs. It needs Yazi, chezmoi,
tmux, and the uv-managed Python.

The unit suite and probes executed inside Yazi remain Lua. Process control,
fixtures, and benchmark orchestration use Python. Neovim is not required.
Set `KEEP_FIXTURE=1` to retain a runtime-suite directory for debugging. The
E2E suite uses `--keep`. The public age example key in the fixture is only for
disposable test data.

See [validation](docs/validation.md) for evidence and remaining platform limits,
and [design](docs/design.md) for the accepted decisions and rationale.

## License

MIT. The linemode integration follows the approach of
[git.yazi](https://github.com/yazi-rs/plugins/tree/main/git.yazi); the applicable
yazi-rs copyright notice is retained in [LICENSE](LICENSE).
