# Commands

What each action runs on, what it asks before running, and what happens
while chezmoi has the terminal. The [README](../README.md#commands) has the
table of commands; [Configuration](configuration.md) has the options, the
theme and what the background status queries run.

## Targets

Actions commit any visual select or unset range, then snapshot the active tab's
selection, including selected files in other directories. With no selection,
they use the hovered file. Empty targets never become an unscoped chezmoi command.
Remote URLs, targets outside the destination, source-tree paths, unavailable files,
and unsupported file types are rejected.
Fresh managed information is required; known inapplicable targets stop the
whole selection before execution. Edit requires individual files or symlinks,
not directories. External, removal, and script entries cannot be edited,
forgotten, or destroyed through these actions.

## Directories and recursion

Directories include descendants by default. `add`, `re-add`, `diff`, `apply`,
and `destroy` accept `--recursive=false` on direct bindings. For `destroy`,
this option accepts files and symlinks but rejects directories: chezmoi still
deletes a directory's descendants with `--recursive=false`. Destroy also rejects
any target containing the source directory, regardless of recursion, to protect
the source state. Recursive parent targets absorb duplicate child selections.
`forget` includes a directory's source descendants and has no nonrecursive option.
Select a managed parent directory to restore missing descendants with apply.
`remove` is unavailable; choose `forget` or `destroy` explicitly. Other CLI flags
are not accepted.

## Confirmations

Single-file add/re-add and opening the editor need no plugin confirmation.
Multiple-target or directory add/re-add operations confirm their scope first.
Forget/destroy always confirm their different effects. Confirmations list
targets in pages sized to the current pane, including continuations of long
paths. Cancelling any page cancels execution. A pane resize restarts review
from the first page; panes smaller than 32 columns or 8 rows must be enlarged
before retrying. Chezmoi's own prompts remain enabled; the plugin never adds
`--force`.

Closing the terminal while one of the plugin's confirmations is open can leave
Yazi running until it is killed with SIGKILL. This is a Yazi bug, seen in
tmux on macOS with Yazi opened in a directory holding files while a plugin
waited in `ya.confirm`; closing a real terminal window was not tried
([validation](validation.md#yazi-outliving-its-terminal)).

## Diff, apply and edit

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

## While a command runs

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
