# chezmoi.yazi

[chezmoi](https://www.chezmoi.io/) knows which of your files it manages and
which would change on the next apply, but it tells you only when you ask.
chezmoi.yazi shows it in [Yazi](https://github.com/sxyazi/yazi)'s file list
as you browse, and runs chezmoi's commands on the files you select.

![Yazi listing a home directory: a C beside each dotfile chezmoi manages, with M on .zshrc and Brewfile, which apply would change, MM on .tmux.conf, edited since the last apply, D on .vimrc, which apply would remove, and a star on .config, which holds such a file; nothing beside .zsh_history, Desktop and the rest, which chezmoi does not manage](docs/images/readme.png)

The picture is the [Quick start](#quick-start) in Ghostty 100 columns wide,
with hidden files shown, on the flavor in
[Theme and flavor](#theme-and-flavor).

- 🏷️ **Status beside each file** — a `C` on every managed file, and the two
  columns `chezmoi status` prints for it.
- 📂 **Directory summaries** — a directory shows when anything managed
  under it differs, files missing from the destination included.
- ⌨️ **Commands on the selection** — add, re-add, edit, diff, apply, forget
  and destroy, on the selected files or the hovered one, from a menu or a
  key of your own.
- 🛡️ **Asks where it matters** — apply shows the diff and asks first,
  forget and destroy always ask, and the plugin never adds `--force`.
- 🎨 **Your theme** — every style and sign can be set in `theme.toml` or a
  flavor.
- 🤝 **Beside git.yazi** — both plugins' signs on the same row.

## Requirements

Yazi **26.9.1**. Older releases refuse to load the plugin, and newer ones are
untested: Yazi changes its plugin API between releases.

chezmoi, found as `chezmoi` on your `PATH` or wherever `setup`'s `command`
points. The test suites last ran in full on macOS with chezmoi 2.73.3, and CI
runs a short end-to-end check with 2.72.2 on Ubuntu 24.04;
[Validation](docs/validation.md) has the earlier runs. Destination paths must
be local Unix paths: Windows and source-tree display are unsupported.

## Installation

```sh
ya pkg add yohkuri/chezmoi
```

If you placed the plugin in `plugins/chezmoi.yazi` yourself, `ya pkg add`
stops and asks you to delete it. Remove it first; if it is a symlink to a
clone, remove only the link itself.

`main` is the release: `ya pkg upgrade` takes its head. chezmoi.yazi supports
one Yazi at a time and moves to the next when its maintainer does, on no
fixed schedule, so a newer Yazi can be out for a while before chezmoi.yazi
follows it.

When it moves, the commit `main` stood at just before is tagged
`yazi-<version>`, naming the Yazi it left: the last chezmoi.yazi for that
Yazi. If your Yazi is older than the one under
[Requirements](#requirements), pin the newest of the
[tags](https://github.com/yohkuri/chezmoi.yazi/tags) whose version is not
above your Yazi's. A Yazi chezmoi.yazi skipped has no tag of its own, and the
tag you pin is untested on it. `ya pkg add` wrote an entry for chezmoi.yazi
in `package.toml`, in Yazi's configuration directory: `$YAZI_CONFIG_HOME`, or
else `$XDG_CONFIG_HOME/yazi`, or else `~/.config/yazi`. Change its `rev` line
to the tag with `=` in front, leave the rest of the entry as it is, and run
`ya pkg install`:

```diff
 [[plugin.deps]]
 use = "yohkuri/chezmoi"
-rev = "daa34ca"
+rev = "=yazi-<version>"
 hash = "34a345d1abf2dfcbfa37bab195979c03"
```

> [!IMPORTANT]
> Keep the `=`. It is what makes `ya pkg upgrade` pass the entry by; without
> it, the next upgrade takes `main`'s head again, which your Yazi refuses.

The `rev` you start from and the `hash` will read differently in yours.
Deleting the `rev` line and running `ya pkg upgrade` returns to `main`. The
tags start at 26.9.1: no release supports an older Yazi. There is one for
each Yazi from there on that chezmoi.yazi has left, and none for the one it
supports now.

## Quick start

```lua
-- ~/.config/yazi/init.lua
require("chezmoi"):setup()
```

```toml
# ~/.config/yazi/yazi.toml
[[plugin.prepend_fetchers]]
url   = "*"
run   = "chezmoi"
group = "chezmoi"

[[plugin.prepend_fetchers]]
url   = "*/"
run   = "chezmoi"
group = "chezmoi"
```

The signs appear beside whichever linemode you have selected. To open the
menu of commands and to refresh the status from a key:

```toml
# ~/.config/yazi/keymap.toml
[[mgr.prepend_keymap]]
on   = ["c", "m"]
run  = "plugin chezmoi -- menu"
desc = "Chezmoi actions"

[[mgr.prepend_keymap]]
on   = ["c", "r"]
run  = "plugin chezmoi -- refresh"
desc = "Refresh chezmoi status"
```

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

The picture at the top is on the
[Catppuccin Mocha](https://github.com/yazi-rs/flavors) flavor, installed with
`ya pkg add yazi-rs/flavors:catppuccin-mocha`, with the plugin's colors
taken from its palette:

```toml
# ~/.config/yazi/theme.toml
[flavor]
dark  = "catppuccin-mocha"
light = "catppuccin-mocha"

[chezmoi]
managed  = { fg = "#89dceb" }
modified = { fg = "#f9e2af" }
changed  = { fg = "#f9e2af" }
deleted  = { fg = "#f38ba8" }
```

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

## Alongside git.yazi

Install [git.yazi](https://github.com/yazi-rs/plugins/tree/main/git.yazi)
with `ya pkg add yazi-rs/plugins:git` and set it up as its README says, with
its own `setup` call and its own fetchers in the `git` group, beside the
`chezmoi` ones. chezmoi.yazi's default `order` is `1600`, after git.yazi's
default `1500`, so git.yazi's sign comes first; set either plugin's `order`
to change that.

## Documentation

- [Commands](docs/commands.md) — what each action runs on, what it asks
  before running, and what happens while chezmoi has the terminal
- [Configuration](docs/configuration.md) — every `setup` option, refresh,
  the theme keys, and what the background status queries run
- [Design](docs/design.md) — the accepted decisions and their reasons
- [Validation](docs/validation.md) — what has been tested, on which
  platforms, and what remains unverified

## Contributing

Bug reports and pull requests are welcome; see
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. The linemode integration follows the approach of
[git.yazi](https://github.com/yazi-rs/plugins/tree/main/git.yazi); the applicable
yazi-rs copyright notice is retained in [LICENSE](LICENSE).
