#!/usr/bin/env -S uv run --locked
"""Persistent, isolated fixture for test/MANUAL.md."""
import argparse
import json
import shlex
import shutil
import sys
import subprocess
from support import REPO, Runtime, baseline, chezmoi_args, environment, owned, run, stop, write


def open_fixture(root):
    """Use the caller's terminal directly; keep the fixture for further checks."""
    print(f"Checklist: {REPO}/test/MANUAL.md", flush=True)
    try:
        return subprocess.run(["yazi", str(root / "dest")], cwd=root,
                              env=environment(root)).returncode
    finally:
        print("Fixture retained. For checklist commands in this or another terminal:")
        print("export CHEZMOI_YAZI_FIXTURE=" + shlex.quote(str(root)))
        print("Reopen: test/manual.py open " + shlex.quote(str(root)))


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
            baseline(t)
            write(t.root / "baseline-theme.toml", '[git]\nuntracked_sign="G "\n' if args.git_plugin else "")
            write(t.root / "manual.json", json.dumps(dict(version=1, root=str(t.root), repo=str(REPO))))
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
            shutil.rmtree(root)
            print(f"Removed manual fixture: {root}")
        else:
            print(run(["chezmoi", *chezmoi_args(root), "status", "--include=all", "--exclude=none",
                       "--path-style=absolute", "--recursive=true"], cwd=root, env=environment(root)), end="")


if __name__ == "__main__":
    sys.exit(main())
