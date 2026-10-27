#!/usr/bin/env -S uv run --locked
"""Open the Yazi the README's picture is taken from, in this terminal.

The configuration is the README's own: the blocks under each of SECTIONS that
name their file on their first line, written out as they stand, with
`show_hidden` added to yazi.toml, as the README says of the picture. The
plugin is this checkout, and each flavor theme.toml names is linked from
where `ya pkg add` put yours. The dotfiles are built in a scratch home that
Yazi and chezmoi are given as HOME, so the header reads ~ and nothing of
your own Yazi, chezmoi or dotfiles reaches it. Before Yazi opens,
`chezmoi status` must print STATUS, so the picture shows each state it is
meant to.

Nothing here sets the terminal up, since nothing could for every terminal;
the `test/readme.py` section of CONTRIBUTING.md says how to take the
picture. This waits for the window to be COLS wide and as tall as the home's entries
with the header and the status bar, opens Yazi with .zshrc hovered, and
removes the scratch home when Yazi quits.

Not in CI, since it needs a person at a real terminal, and not checked
against the PNG: retake the picture when what the setup draws changes.
"""
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

from support import REPO, read, run, write

# The README's sections the picture's configuration comes from, with the files each must name.
SECTIONS = {"## Quick start": ["init.lua", "yazi.toml", "keymap.toml"], "## Theme and flavor": ["theme.toml"]}
# The first line of a block that names its file, in Lua's or TOML's comment.
NAMED = re.compile(r"(?:--|#) ~/\.config/yazi/(\S+)")
# What the README says the picture adds to the Quick start.
HIDDEN = "\n[mgr]\nshow_hidden = true\n"

# The source's files, as chezmoi applies them before the changes below.
SOURCE = {
    ".chezmoiignore": "README.md\n",
    "Brewfile": 'brew "chezmoi"\nbrew "git"\nbrew "yazi"\n',
    "dot_config/git/ignore": ".DS_Store\n",
    "dot_config/nvim/init.lua": "vim.o.number = true\nvim.o.expandtab = true\n",
    "dot_config/starship.toml": "add_newline = false\n",
    "dot_editorconfig": "root = true\n\n[*]\nindent_style = space\nindent_size = 2\n",
    "dot_gitconfig": "[user]\n\tname = You\n\temail = you@example.com\n[init]\n\tdefaultBranch = main\n",
    "dot_inputrc": "set completion-ignore-case on\n",
    "dot_local/bin/executable_git-prune-merged": "#!/bin/sh\ngit branch --merged | grep -v main | xargs git branch -d\n",
    "dot_tmux.conf": "set -g mouse on\nset -g base-index 1\n",
    "dot_vimrc": "set number\nsyntax on\n",
    "dot_zprofile": 'eval "$(/opt/homebrew/bin/brew shellenv)"\n',
    "dot_zshenv": 'export XDG_CONFIG_HOME="$HOME/.config"\n',
    "dot_zshrc": ("export EDITOR=nvim\nexport PATH=\"$HOME/.local/bin:$PATH\"\n\nalias ll='ls -lh'\nalias g=git\n\n"
                  'eval "$(starship init zsh)"\n'),
    "private_dot_ssh/private_config": "Host *\n  AddKeysToAgent yes\n  UseKeychain yes\n",
    "README.md": "# dotfiles\n",
}
# What a home holds beside the dotfiles, none of it managed.
UNMANAGED = {
    ".cache/starship/session.log": "",
    ".lesshst": ".less-history-file:\n",
    ".ssh/known_hosts": "github.com ssh-ed25519 AAAA\n",
    ".zsh_history": ": 1761300000:0;chezmoi status\n",
    "Desktop/Screenshot.png": "",
    "Documents/notes.md": "",
    "Downloads/yazi.zip": "",
    "Pictures/wallpaper.jpg": "",
}
# One change for each state the picture shows, after the first apply.
SRC = ".local/share/chezmoi/"
EDITS = {
    SRC + "dot_zshrc": SOURCE["dot_zshrc"] + 'eval "$(mise activate zsh)"\n',
    SRC + "Brewfile": SOURCE["Brewfile"] + 'brew "uv"\n',
    SRC + "dot_config/nvim/init.lua": SOURCE["dot_config/nvim/init.lua"] + "vim.o.wrap = false\n",
    ".tmux.conf": SOURCE["dot_tmux.conf"] + "set -g status-position top\n",
    SRC + ".chezmoiremove": ".vimrc\n",
}
GONE = [SRC + "dot_vimrc", ".config/git/ignore"]
STATUS = """\
DA .config/git/ignore
 M .config/nvim/init.lua
MM .tmux.conf
 D .vimrc
 M .zshrc
 M Brewfile
"""
HOVER = ".zshrc"
# Beside the home, so the parent pane is not empty.
SIBLINGS = ["Shared"]

COLS = 100
# What a window closing, a kill or Ctrl-C sends this script.
SIGNALS = [signal.SIGHUP, signal.SIGTERM, signal.SIGINT]


def setup_blocks(text, section, files):
    """The blocks under section for each of files, by name; ValueError if one is missing or named twice.

    A block naming any other file is skipped: it is written nowhere, so it cannot reach through the
    links to this checkout or your flavors."""
    lines = text.splitlines()
    try:
        start = lines.index(section) + 1
    except ValueError:
        raise ValueError(f"no `{section}` heading") from None
    blocks, fence = {}, None
    for i in range(start, len(lines)):
        # A heading at the section's level or above ends it; a `#` comment in a block does not.
        if fence is None and re.match(r"#{1,2} ", lines[i]):
            break
        if fence is None and lines[i].startswith("```"):
            fence = i
        elif fence is not None and lines[i] == "```":
            body = lines[fence + 1:i]
            named = NAMED.fullmatch(body[0]) if body else None
            if named and named.group(1) in files:
                name = named.group(1)
                if name in blocks:
                    raise ValueError(f"line {fence + 1}: a second `{name}` block")
                block = "\n".join(body) + "\n"
                if name.endswith(".toml"):
                    try:
                        tomllib.loads(block)
                    except tomllib.TOMLDecodeError as error:
                        raise ValueError(f"line {fence + 1}: `{name}` is not TOML: {error}") from None
                blocks[name] = block
            fence = None
    missing = [name for name in files if name not in blocks]
    if missing:
        raise ValueError(f"no {', '.join(f'`{name}`' for name in missing)} block under `{section}`")
    return blocks


def picture_blocks(text):
    """The picture's files: each of SECTIONS' blocks, with HIDDEN added to yazi.toml."""
    blocks = {}
    for section, files in SECTIONS.items():
        blocks.update(setup_blocks(text, section, files))
    blocks["yazi.toml"] += HIDDEN
    try:
        tomllib.loads(blocks["yazi.toml"])
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"`yazi.toml` with `show_hidden` added is not TOML: {error}") from None
    return blocks


def flavors(theme):
    """The flavors a theme.toml names, in either slot."""
    named = tomllib.loads(theme).get("flavor", {})
    return {name for name in named.values() if isinstance(name, str) and name} if isinstance(named, dict) else set()


def installed():
    """Your Yazi's configuration directory, where `ya pkg add` puts flavors, as Yazi finds it."""
    for key, below in [("YAZI_CONFIG_HOME", ""), ("XDG_CONFIG_HOME", "yazi")]:
        if os.path.isabs(os.environ.get(key, "")):
            return Path(os.environ[key], below)
    return Path.home() / ".config/yazi"


def environment(home, root):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CHEZMOI_", "YAZI_", "PYTHON"))}
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"), XDG_DATA_HOME=str(home / ".local/share"),
               XDG_STATE_HOME=str(home / ".local/state"), XDG_CACHE_HOME=str(home / ".cache"), YAZI_LOG="warn")
    # chezmoi falls back to these for its configuration and source, so they point at nothing outside the home,
    # and out of the parent pane's sight.
    env.update(XDG_CONFIG_DIRS=str(root / "xdg"), XDG_DATA_DIRS=str(root / "xdg"))
    return env


def build(home, blocks, links, env):
    """The scratch home, with STATUS's changes on top of a first apply, and links' flavors by name."""
    config = home / ".config/yazi"
    for directory in ["plugins", "flavors"]:
        (config / directory).mkdir(parents=True)
    (config / "plugins/chezmoi.yazi").symlink_to(REPO)
    for name, path in links.items():
        (config / f"flavors/{name}.yazi").symlink_to(path)
    for name in SIBLINGS:
        (home.parent / name).mkdir()
    for name, block in blocks.items():
        write(config / name, block)
    for base, files in [(home / SRC, SOURCE), (home, UNMANAGED)]:
        for name, text in files.items():
            (base / name).parent.mkdir(parents=True, exist_ok=True)
            write(base / name, text)
    run(["chezmoi", "apply"], env=env)
    for name in GONE:
        (home / name).unlink()
    for name, text in EDITS.items():
        write(home / name, text)
    status = run(["chezmoi", "status"], env=env)
    if status != STATUS:
        raise ValueError(f"chezmoi status printed\n{status}rather than\n{STATUS}")


def wait_for_window(rows, notes):
    """Return once the terminal is COLS x rows; no terminal can be sized in cells from in here.

    The notes and the request are redrawn on a cleared screen whenever the size changes, cut to the width:
    a line printed at the old width would be rewrapped by a narrower window and left behind."""
    shown = None
    while True:
        size = os.get_terminal_size()
        if (size.columns, size.lines) == (COLS, rows):
            return
        if size != shown:
            lines = [*notes, f"Resize to {COLS}x{rows} (now {size.columns}x{size.lines}); Ctrl-C quits."]
            print("\033[H\033[J" + "\n".join(line[:size.columns - 1] for line in lines), end="", flush=True)
            shown = size
        time.sleep(0.2)


def hold_signals():
    """Ignore SIGNALS, so a second one cannot cut short what the first one started."""
    for number in SIGNALS:
        signal.signal(number, signal.SIG_IGN)


def open_yazi(home, env):
    """Run Yazi in the foreground and return its exit code."""
    child = None
    # Ctrl-C belongs to Yazi and the pager or editor it hands the terminal to, not this waiting parent,
    # and after Yazi only the cleanup is left, so it is not given back. A caught handler resets on exec,
    # so they still receive it.
    signal.signal(signal.SIGINT, lambda *_: None)
    try:
        child = subprocess.Popen(["yazi", str(home / HOVER)], cwd=home, env=env)
        return child.wait()
    except BaseException:
        hold_signals()
        # Let Yazi restore the terminal before the scratch home goes: in a private tmux it took 5 seconds
        # to quit on SIGTERM.
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        raise


def failure(error):
    """What went wrong building the home: `support.run` fails with its command, exit code and stderr."""
    if isinstance(error, AssertionError) and error.args and isinstance(error.args[0], tuple):
        args, code, stderr = error.args[0]
        return f"`{shlex.join(args)}` exited {code}:\n{stderr.rstrip()}"
    return str(error)


def main(argv):
    if argv:
        sys.exit("usage: test/readme.py")
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        sys.exit("readme: run this in the terminal the picture is taken in")
    for command in ["yazi", "chezmoi"]:
        if not shutil.which(command):
            sys.exit(f"readme: {command} is not on PATH")
    try:
        blocks = picture_blocks(read(REPO / "README.md"))
        links = {name: installed() / f"flavors/{name}.yazi" for name in flavors(blocks["theme.toml"])}
    except ValueError as error:
        sys.exit(f"readme: README.md: {error}")
    for name, path in sorted(links.items()):
        if not path.is_dir():
            sys.exit(f"readme: the README's theme.toml names the flavor {name}, and there is no "
                     f"{path} to link it from: `ya pkg add` it")
    notes = ["readme: inside tmux, whose status bar would be in the picture"] if os.environ.get("TMUX") else []
    # Closing the window or a kill would otherwise skip the cleanup below.
    for number in [signal.SIGHUP, signal.SIGTERM]:
        signal.signal(number, lambda number, _: sys.exit(128 + number))
    root = Path(tempfile.mkdtemp(prefix="chezmoi-yazi-readme-")).resolve()
    try:
        home = root / "Users/you"
        env = environment(home, root)
        try:
            build(home, blocks, links, env)
        except (ValueError, AssertionError, subprocess.TimeoutExpired) as error:
            print(f"readme: {failure(error)}", file=sys.stderr)
            return 1
        # A row for each entry of the home, with the header and the status bar.
        rows = len(list(home.iterdir())) + 2
        try:
            wait_for_window(rows, notes)
        except KeyboardInterrupt:
            print()
            return 130
        code = open_yazi(home, env)
        # Read before the scratch home goes, since the log goes with it.
        log = home / ".local/state/yazi/yazi.log"
        trouble = log.exists() and read(log).strip()
        if trouble:
            print("readme: Yazi logged trouble, which the picture may show:\n" + trouble, file=sys.stderr)
            return 1
        if code:
            print(f"readme: Yazi exited {code}", file=sys.stderr)
            return 1
    finally:
        # A second signal, as closing a window can send, must not cut the removal short.
        hold_signals()
        shutil.rmtree(root)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
