# Manual acceptance checklist

Use a disposable destination to inspect the actual terminal display. Run the
commands below from this repository's root. Public documentation is English;
Unicode names in the fixture are intentional test data.

## Requirements and preparation

You need Yazi 26.9.1+, chezmoi, and uv on `PATH`. The baseline
is macOS, Yazi 26.9.1, and chezmoi 2.72.2. Linux remains unverified. Allow a
terminal at least 100 columns wide; resize later to inspect clipping.

Install uv 0.11.19 using your preferred installer. mise is optional and is
only a way to install pinned tool versions. The executable script invokes uv
and prepares Python 3.14 and the locked environment automatically; no pip
packages, Neovim, or separate Python setup command are needed. Lua is needed
for development checks, but not for launching the manual fixture.
Keep this checkout and its `.venv` in place while a fixture is active.
Its wrapper uses that Python interpreter.

Create a fresh fixture:

```sh
test/manual.py
```

The command creates the fixture and opens Yazi directly in your current
terminal, including when that terminal is already inside tmux. No tmux server
or attach command is needed. Press `q` to return to the shell; the fixture is
retained. The helper then prints an `export CHEZMOI_YAZI_FIXTURE=...` command.
For the two-terminal checks below, copy that export into both terminals and
reopen Yazi in the first one:

```sh
test/manual.py open "$CHEZMOI_YAZI_FIXTURE"
```

To test git.yazi coexistence, create a separate fixture instead:

```sh
test/manual.py \
  --git-plugin "$HOME/.config/yazi/plugins/git.yazi"
```

The helper initializes a Git repository only inside the disposable destination.
It does not stage or commit anything. The supplied git.yazi checkout is used
read-only. Its untracked marker is set to `"G "` for easy comparison.

Creation opens Yazi immediately after preparing the fixture. Status appears
as the plugin fetches it; inspect the expected `MM` row below.
The plugin is symlinked to
this checkout; restart with a fresh fixture after changing plugin code.

### What the fixture contains

| Path below the printed root | Purpose |
| --- | --- |
| `source/` | Disposable chezmoi source state |
| `dest/` | Destination shown in Yazi |
| `chezmoi.toml`, `chezmoi.db` | Isolated configuration and last-written state |
| `config/` | Isolated Yazi config, keymaps, plugin symlinks, and themes |
| `state/`, `cache/`, `data/` | Isolated XDG paths |
| `state/instrument/calls` | JSON lines recording plugin command arguments |
| `state/instrument/report.json` | State snapshot, updated by pressing `T` |
| `state/instrument/control` | Optional injected failure control |
| `initial.diff` | Scoped diff captured before initial fixture apply |
| `manual.json` | Ownership marker required for cleanup |

Only the explicitly named ordinary fixture files are applied at creation.
The pending apply script is added afterward. Nothing in your normal chezmoi
source/destination or Yazi configuration is changed. Do not run a bare
`chezmoi apply` during this checklist. Edits below affect only fixture files.

### Fixture keymap

Keys are case-sensitive; use Shift for the uppercase keys.

| Key | Action |
| --- | --- |
| `j`, `k` or arrows | Move the cursor |
| `l` / Right, `h` / Left | Enter a directory / go to its parent |
| `R` | Refresh chezmoi membership and status |
| `Y` | Reload theme without refreshing status |
| `T` | Write a diagnostic state snapshot |
| `N` | Go to fixture `.config` |
| `B` | Return to fixture destination root |
| `G` | Open fixture `.config` in a new tab |
| `H` | Switch to tab zero |
| `q` | Quit Yazi |

`R`, `Y`, `T`, `N`, `B`, `G`, and `H` override normal Yazi bindings only in this
fixture. Hidden files are visible and the base linemode is `none` so the
plugin columns are easy to identify.

## 1. Initial membership and status

Inspect each row both hovered and unhovered. Spaces in the following displays
are significant; quotation marks are explanatory, not rendered. The layout
is `MXYD`, with an additional leading separator space. The last slot is the
directory summary, reserved but blank for ordinary files.

| Destination name | Expected display | Reason |
| --- | --- | --- |
| `clean`, `bad` | `"C   "` | Managed and unchanged |
| `local` | `"CMM "` | Edited after initial apply |
| `source` | `"C M "` | Source changed after initial apply |
| `unmanaged`, `ignored` | `"    "` | Not managed / ignored by chezmoi |
| `remove-me` | `"C D "` | Removal declared in `.chezmoiremove` |
| `link` | `"C   "` | Managed symlink to `clean` |
| `.config` | `"C  *"` | Missing managed child and pending script |
| `.exact` | `"C  *"` | Extra destination entry in an exact directory |

Enter `.exact`: `extra` should have `"C D "`, even though there is no ordinary
source file for it. Enter `.config`: missing targets contribute to the parent
summary but do not create artificial file rows. Press `B` to return.

Compare against the same isolated chezmoi context in the second terminal:

```sh
test/manual.py status \
  "$CHEZMOI_YAZI_FIXTURE"
```

Clean and unmanaged files are omitted from `chezmoi status`; plugin membership
also uses `chezmoi managed`. A pending script produces an `R` in chezmoi's
second column. Its absence from the destination is intentional. Confirm that
status acquisition has not executed it:

```sh
test ! -e "$CHEZMOI_YAZI_FIXTURE/script-ran" && echo 'PASS: script not executed'
```

With git.yazi enabled, look for `"G "` before the chezmoi columns on the same
untracked row. The git marker must not replace or hide the `CMM` display.

## 2. Names, alignment, and selected-row colors

Inspect `space name`, `日本語`, `quote"name`, `back\slash`, and `-dash`.
Each starts clean and managed. There are also filenames containing a literal
newline and carriage return. Yazi may escape or substitute their presentation;
their plugin records must still be managed and clean.

Press `T`, then inspect `state/instrument/report.json` if a filename is hard to
identify. JSON escapes preserve its exact path. Move the cursor through all
rows: hovered signs inherit Yazi's selection colors. Resize the terminal and
check column spacing, contrast, and clipping visually.

## 3. Manual refresh and resolution

In the second terminal, make the source match the locally edited file:

```sh
cp "$CHEZMOI_YAZI_FIXTURE/dest/local" "$CHEZMOI_YAZI_FIXTURE/source/local"
```

Press `R`. `local` must change from `"CMM "` to `"C   "`. A brief unknown
marker while querying is expected. To restore the original test state:

```sh
printf 'original\n' > "$CHEZMOI_YAZI_FIXTURE/source/local"
```

Press `R` and expect `"CMM "` again. Editing source files outside the visible
folder does not guarantee an automatic refresh; the plugin has no polling loop.

## 4. Membership discovery and removal

```sh
cp "$CHEZMOI_YAZI_FIXTURE/dest/unmanaged" \
  "$CHEZMOI_YAZI_FIXTURE/source/unmanaged"
```

Press `R`: `unmanaged` becomes `"C   "`. Then remove only its source entry:

```sh
rm -- "$CHEZMOI_YAZI_FIXTURE/source/unmanaged"
```

Press `R`: its destination file remains, but the `C` marker disappears.

## 5. Template failure and recovery

```sh
mv "$CHEZMOI_YAZI_FIXTURE/source/bad" "$CHEZMOI_YAZI_FIXTURE/source/bad.tmpl"
printf '{{ .missing.field }}\n' > "$CHEZMOI_YAZI_FIXTURE/source/bad.tmpl"
```

Press `R`. `bad` must display `"C!! "`; `clean` must remain `"C   "`.
A generic warning can appear, without template contents or raw stderr.
Warnings are throttled, so another immediate failure need not show a new toast.
A full `status` helper invocation can fail while this template is broken;
the plugin's scoped recovery can still retain successful independent rows.

Restore the template contents and press `R`:

```sh
printf 'original\n' > "$CHEZMOI_YAZI_FIXTURE/source/bad.tmpl"
```

`bad` must return to `"C   "`. To check partial directory coverage:

```sh
printf '{{ .missing.field }}\n' \
  > "$CHEZMOI_YAZI_FIXTURE/source/dot_config/broken.tmpl"
```

Press `R`. `.config` still shows `*` because a difference is known, with the
`partial` underline style because another descendant failed. After inspecting:

```sh
rm -- "$CHEZMOI_YAZI_FIXTURE/source/dot_config/broken.tmpl"
```

Press `R` and confirm the underline disappears.

## 6. Failed membership acquisition

```sh
printf 'fail-managed' > "$CHEZMOI_YAZI_FIXTURE/state/instrument/control"
```

Press `R`. Ordinary file rows show `"!   "`, not a clean or unmanaged result;
directories additionally show an error in their summary slot. Restore:

```sh
rm -- "$CHEZMOI_YAZI_FIXTURE/state/instrument/control"
```

Press `R` and compare with the known statuses. This failure injection affects
only the plugin wrapper; the `status` helper runs the real chezmoi directly.

## 7. Navigation and tabs

Press `N`, then edit `source/source` from the second terminal:

```sh
cp "$CHEZMOI_YAZI_FIXTURE/dest/source" "$CHEZMOI_YAZI_FIXTURE/source/source"
```

Press `B`. The `source` row should become clean when the acquisition finishes.
Press `G`, then `H` to return through a tab switch, and verify consistent state.
Do not create multiple tabs before this step; `H` always selects tab zero.

## 8. Theme override and flavor fallback

Create an isolated flavor in the second terminal:

```sh
mkdir -p "$CHEZMOI_YAZI_FIXTURE/config/flavors/manual.yazi"
cat > "$CHEZMOI_YAZI_FIXTURE/config/flavors/manual.yazi/tmtheme.xml" <<'XML'
<?xml version="1.0"?><plist version="1.0"><dict><key>name</key><string>manual</string><key>settings</key><array/></dict></plist>
XML
cat > "$CHEZMOI_YAZI_FIXTURE/config/flavors/manual.yazi/flavor.toml" <<'TOML'
[chezmoi]
managed_sign = "F"
modified_sign = "m"
modified = { fg = "#ff8800" }
TOML
cp "$CHEZMOI_YAZI_FIXTURE/baseline-theme.toml" \
  "$CHEZMOI_YAZI_FIXTURE/config/theme.toml"
cat >> "$CHEZMOI_YAZI_FIXTURE/config/theme.toml" <<'TOML'
[flavor]
dark = "manual"
light = "manual"
[chezmoi]
managed_sign = "界"
TOML
```

Press `Y`. Expect `界` from the theme, with `m` and orange modified text from
the flavor. Unhover `local` to inspect its color; hovered text inherits the
row highlight. Other rows should remain aligned despite the wide sign.
Status values must not change when reloading the theme. Press `T` to inspect
`signs` and `epoch` before and after `Y`; the epoch should remain unchanged
if no navigation or manual status refresh intervened.

Restore the default theme:

```sh
cp "$CHEZMOI_YAZI_FIXTURE/baseline-theme.toml" \
  "$CHEZMOI_YAZI_FIXTURE/config/theme.toml"
```

Press `Y`. Default signs return, preserving `"G "` when git.yazi is enabled.

## 9. Evidence and cleanup

Record versions, terminal name, failed step, expected/actual display, and a
screenshot when reporting a visual issue. Press `T` for a fresh state snapshot.
Logs are under the fixture's `state/`; command arguments are in
`state/instrument/calls`. Keep the fixture until you have saved useful evidence.

Press `q` to return to the shell. Use `test/manual.py open` with the fixture
path to resume. To remove the fixture after exiting Yazi, run:

```sh
test/manual.py clean \
  "$CHEZMOI_YAZI_FIXTURE"
unset CHEZMOI_YAZI_FIXTURE
```

Cleanup checks the root and ownership marker and removes only that fixture.
Exit any Yazi instances using it before cleanup. No manual tmux server is
created; cleanup still handles private sockets from older fixtures.
A fresh `create` produces the original baseline; it does not overwrite or
reset an existing fixture. Clean each fixture separately if you created more
than one. A missing/mismatched ownership marker causes cleanup to refuse.

## Automated coverage and limits

This checklist is for human inspection and repeatable edits. It does not claim
that every provider, font, or platform is supported. Encryption failure,
timeout handling, stale-generation cancellation, and exact process-count
checks have automated coverage in `test/runtime.py`; see
[validation](../docs/validation.md). Screen-visible status, refresh,
navigation, failure recovery, and theme reload have black-box coverage in
`test/e2e.py`. To run the automated suites separately:

```sh
test/runtime.py
test/e2e.py
```

`KEEP_FIXTURE=1` on the runtime suite preserves its **final mutated state**
after the session stops; use `--keep` with the E2E suite. Use `test/manual.py`
for the initial states in this checklist.
