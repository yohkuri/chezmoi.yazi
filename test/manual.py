#!/usr/bin/env -S uv run --locked
"""Launch a guided manual walk entirely inside one Yazi terminal session."""
import argparse
import json
import shutil
import sys
import subprocess
from support import REPO, Runtime, chezmoi_args, environment, owned, run, stop, write


def configure_guide(t, git_plugin):
    from manual_backend import initialize
    initial = initialize(t.root, git_plugin)
    install_guide(t, initial, git_plugin)
    keys = {"W": "plugin manual", "Y": "app:theme", "T": "plugin probe", "<Space>": "toggle", "q": "plugin manual -- exit", "S": "escape --select",
            "C": "plugin manual -- action menu", "R": "plugin manual -- action refresh",
            "a": "plugin manual -- action add", "r": "plugin manual -- action re-add",
            "e": "plugin manual -- action edit", "E": "plugin manual -- action edit --apply",
            "p": "plugin manual -- action apply", "d": "plugin manual -- action diff",
            "f": "plugin manual -- action forget", "x": "plugin manual -- action destroy",
            "D": "plugin manual -- action destroy --recursive=false",
            "t": "plugin manual -- action add --template", "z": "plugin manual -- action add --encrypt"}
    keys.update({key: "plugin manual -- nav " + key for key in "NBGH1234567890"})
    write(t.root / "config/keymap.toml", ''.join(
        f'[[mgr.prepend_keymap]]\non={json.dumps(k)}\nrun={json.dumps(v)}\n' for k, v in keys.items()))
    return initial


def install_guide(t, initial, git_plugin):
    from support import lua
    t.plugin("manual", dict(python=sys.executable, backend=REPO / "test/manual_backend.py",
                            session=t.root, initial=initial))
    write(t.root / "config/init.lua", 'require("chezmoi"):setup ' + lua(initial["opts"]) + '\n'
          + ('require("git"):setup()\n' if git_plugin else '') + 'require("manual"):setup()\n')

def open_fixture(root):
    """One foreground Yazi process; archive and clean only after it exits."""
    if not (root / "walk.json").exists():
        raise ValueError("Legacy fixture: create a new guided session with test/manual.py")
    from manual_backend import current, finalize, load
    _, state = load(root)
    from manual_backend import save, view
    state.pop("exit", None)
    current(state)["epoch_before"] = None
    save(root, state)
    t = Runtime.__new__(Runtime)
    t.root = root
    install_guide(t, view(state), state["git_plugin"])
    destination = current(state)["opts"]["destination"]
    print("W: guide controls and full instructions. q: results and finish.", flush=True)
    child = None
    try:
        child = subprocess.Popen(["yazi", destination], cwd=root, env=environment(root))
        code = child.wait()
        if code:
            _, state = load(root)
            state["exit"] = {"keep": True}
            save(root, state)
        return code
    except BaseException:
        # Archive/cleanup must never race a live foreground Yazi.
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        _, state = load(root)
        state["exit"] = {"keep": True}
        save(root, state)
        raise
    finally:
        try:
            finalize(root)
        except Exception:
            print(f"Could not archive results; all fixtures retained: {root}", file=sys.stderr)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     epilog="With no command, create a fresh fixture.")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("create").add_argument("--git-plugin")
    for action in ["status", "clean", "open"]:
        sub.add_parser(action).add_argument("fixture")
    arguments = sys.argv[1:]
    if not arguments or arguments[0].split("=", 1)[0] == "--git-plugin":
        arguments.insert(0, "create")
    args = parser.parse_args(arguments)
    if args.action in {"create", "open"} and not (sys.stdin.isatty() and sys.stdout.isatty()):
        parser.error("Run this command in an interactive terminal.")
    if args.action == "create":
        t = Runtime(args.git_plugin)
        try:
            write(t.root / "baseline-theme.toml", '[git]\nuntracked_sign="G "\n' if args.git_plugin else "")
            write(t.root / "manual.json", json.dumps(dict(version=1, root=str(t.root), repo=str(REPO))))
            configure_guide(t, args.git_plugin)
        except BaseException:
            t.close()
            raise
        return open_fixture(t.root)
    else:
        root = owned(args.fixture)
        if args.action == "open":
            return open_fixture(root)
        if args.action == "clean":
            stop(root)
            if (root / "walk.json").exists():
                from manual_backend import load
                _, state = load(root)
                for attempt in state["attempts"]:
                    shutil.rmtree(owned(attempt["root"]))
            shutil.rmtree(root)
            print(f"Removed manual fixture: {root}")
        else:
            if (root / "walk.json").exists():
                from manual_backend import context, current, load
                _, state = load(root)
                t = context(current(state)["root"])
                print(t.chezmoi("status", "--include=all", "--exclude=none", "--path-style=absolute", "--recursive=true"), end="")
                return 0
            print(run(["chezmoi", *chezmoi_args(root), "status", "--include=all", "--exclude=none",
                       "--path-style=absolute", "--recursive=true"], cwd=root, env=environment(root)), end="")


if __name__ == "__main__":
    sys.exit(main())
