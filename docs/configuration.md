# Configuration

Every `setup` option, how the display refreshes, the theme keys, and what the
background status queries run. The [README](../README.md) has the short
version; [Commands](commands.md) covers the actions.

## `setup` options

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
  notify_timeout = 7,            -- least seconds a command notification shows
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
`notify_timeout` covers the notifications that commands show, such as a
rejected target or a completed command; the warning that status is
unavailable keeps its 5 seconds. It takes 0.001 to 1e9 seconds. Yazi shows
up to three notifications at a time, as many as fit the height, starts a
queued one's time only when it shows, and keeps a new one longer while older
ones are showing, so one can stay longer than this.

Large directories can cover most of the managed tree. Smaller timeouts or a
lower retry budget trade completeness for latency; failed coverage remains
explicit. Each acquisition pass refreshes the managed index, so new and
forgotten entries and dynamically generated removals can be discovered.

## Refresh behavior

Queries run asynchronously on fetcher activity and directory navigation.
Requests share one worker; results are reused briefly to avoid duplicate work.
There is **no periodic polling**. External source/template edits while the
view is stationary may require `plugin chezmoi -- refresh`. That command
refreshes membership and the current file list immediately, invalidating
older work.

An automatic refresh can display old results with the `stale` style while
working. Once a query fails, failure signs replace the old status. Manual
refresh and navigation clear old results immediately. Failure notifications
are limited to one per 30 seconds and never include raw stderr or secrets.

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

Background status acquisition calls `execute-template` for the destination
and source directories, `managed`, and `status`; it never calls mutation
commands. Templates and encrypted files are evaluated by chezmoi, with all
entry categories included and secret skipping disabled.
Thus configured `include`/`exclude` preferences for a bare status command are
intentionally overridden. Apply scripts are reported, not executed.

Background queries use argument arrays, closed stdin, `--no-tty`, no pager/color/progress,
and a timeout. Missing credentials or invalid templates produce failure signs.
chezmoi hooks, template functions, decryptors, and external resources may still
run commands, refresh caches, or open their own UI. This is full chezmoi
evaluation, not a sandbox.

The deadline covers reading stdout and waiting for the **direct child**, even
when that child is silent or closes stdout before exiting. Timeout termination
does not guarantee termination of arbitrary grandchildren, and the guarantee
does not cover a query still running when Yazi exits. The output limit
is checked after each line read; it is not a strict peak-memory limit for one
very large unterminated line. Cancellation takes effect between reads, at
latest after the current command's timeout. A pass may contain multiple
commands, each with its own deadline; a cancelled pass starts no further
commands.

NUL-separated managed paths and validated status coverage prevent failed or
ambiguous output from becoming a false clean result. CR/LF filenames require
individual nonrecursive queries because status has no NUL output format.
Membership and status are separate snapshots; concurrent filesystem changes
can produce a failure until the next refresh.
