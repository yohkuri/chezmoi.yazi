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

Status is queried in the background when Yazi fetches files or you change
directory, and results are reused briefly. There is **no periodic polling**:
after editing the source outside Yazi, run `plugin chezmoi -- refresh`.
While an automatic refresh runs, old results can show in the `stale` style;
a failed query shows failure signs instead.
[Configuration](docs/configuration.md#refresh-behavior) has the details.

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

Actions run on the active tab's selection, or on the hovered file when
nothing is selected, and never become an unscoped chezmoi command.
Directories include their descendants; some commands take
`--recursive=false`. Apply always shows the diff and asks first; forget and
destroy always ask, and add and re-add ask when they take several targets or
a directory. The plugin never adds `--force`, and chezmoi's own prompts stay
on. A diff is a preview: chezmoi evaluates again at apply time. A failed
command may leave partial changes, with no retry or rollback.
[Commands](docs/commands.md) has the full rules, including which commands
take `--recursive=false`.

## Configuration

`setup` with no options uses chezmoi's usual configuration and destination;
[Configuration](docs/configuration.md#setup-options) lists every option.

## Theme and flavor

Styles and signs come from `[chezmoi]` in `theme.toml` or a flavor's
`flavor.toml`:

```toml
[chezmoi]
managed       = { fg = "blue", bold = true }
modified      = { fg = "lightred" }
modified_sign = "~"
```

[Theme and flavor](docs/configuration.md#theme-and-flavor) lists every key
with its default.

## Evaluation and limits

Background status queries never run mutation commands, and apply scripts are
reported, not executed. They are still full chezmoi evaluation, not a
sandbox: templates and encrypted files are evaluated, and chezmoi hooks,
template functions, decryptors, and external resources may run commands or
open their own UI. A query that runs past its timeout fails, but processes
chezmoi started may outlive it.
[Evaluation and limits](docs/configuration.md#evaluation-and-limits) has the
rest.

Closing the terminal while one of the plugin's confirmations is open can leave
Yazi running until it is killed with SIGKILL; see
[Confirmations](docs/commands.md#confirmations).

## Contributing

Bug reports and pull requests are welcome; see
[CONTRIBUTING.md](CONTRIBUTING.md). See [validation](docs/validation.md) for
evidence and remaining platform limits, and [design](docs/design.md) for the
accepted decisions and rationale.

## License

MIT. The linemode integration follows the approach of
[git.yazi](https://github.com/yazi-rs/plugins/tree/main/git.yazi); the applicable
yazi-rs copyright notice is retained in [LICENSE](LICENSE).
