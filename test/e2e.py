#!/usr/bin/env -S uv run --locked
"""Black-box checks against a real Yazi screen and real chezmoi process."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import traceback

import screen
from support import Runtime, baseline, read, write


def statuses(capture, expected):
    return all(screen.status(capture, name) == value for name, value in expected.items())


def wait_statuses(t, expected, description):
    return t.wait_screen(lambda capture: statuses(capture, expected), description)


def clean_logs(t):
    logs = t.logs()
    assert "Error when running" not in logs and "runtime error:" not in logs, logs


def status_refresh(t):
    sentinel = t.root / "script-ran"
    expected = {
        ".config": "C  *",
        ".exact": "C  *",
        "clean": "C   ",
        "ignored": "    ",
        "local": "CMM ",
        "remove-me": "C D ",
        "source": "C M ",
        "unmanaged": "    ",
    }
    t.start(settle=0)
    wait_statuses(t, expected, "initial managed, unmanaged, and summary values")
    assert not sentinel.exists(), "Status acquisition executed a pending script"

    write(t.source / "local", read(t.dest / "local"))
    t.key("R", settle=0)
    wait_statuses(t, {**expected, "local": "C   "}, "manual refresh to clear local")
    assert not sentinel.exists(), "Manual refresh executed a pending script"
    t.quit()
    clean_logs(t)


def navigation(t):
    sentinel = t.root / "script-ran"
    t.chezmoi("apply", t.dest / ".config/new")
    t.start(settle=0)
    wait_statuses(t, {".config": "C  *", "local": "CMM "}, "root directory values")

    t.key("N", settle=0)
    capture = wait_statuses(t, {"new": "C   "}, "managed row after entering .config")
    assert screen.status(capture, "local") is None

    t.key("B", settle=0)
    wait_statuses(t, {".config": "C  *", "local": "CMM "}, "root values after returning")

    t.key("G", settle=0)
    capture = wait_statuses(t, {"new": "C   "}, "managed row in the new tab")
    assert screen.status(capture, "local") is None

    t.key("H", settle=0)
    wait_statuses(t, {".config": "C  *", "local": "CMM "}, "root values after tab switch")
    assert not sentinel.exists(), "Navigation executed a pending script"
    t.quit()
    clean_logs(t)


def failure_recovery(t):
    t.start(settle=0)
    wait_statuses(t, {"bad": "C   ", "clean": "C   "}, "initial healthy rows")

    (t.source / "bad").rename(t.source / "bad.tmpl")
    write(t.source / "bad.tmpl", "{{ .missing.field }}")
    t.key("R", settle=0)
    wait_statuses(t, {"bad": "C!! ", "clean": "C   "}, "isolated template failure")

    write(t.source / "bad.tmpl", "original\n")
    t.key("R", settle=0)
    wait_statuses(t, {"bad": "C   ", "clean": "C   "}, "template recovery")
    t.quit()
    clean_logs(t)


def theme_reload(t):
    t.start(settle=0)
    wait_statuses(t, {"local": "CMM ", "source": "C M "}, "status before theme reload")

    flavor = t.root / "config/flavors/fixture.yazi"
    flavor.mkdir(parents=True)
    write(
        flavor / "tmtheme.xml",
        '<?xml version="1.0"?><plist version="1.0"><dict><key>name</key>'
        "<string>test</string><key>settings</key><array/></dict></plist>",
    )
    write(
        flavor / "flavor.toml",
        '[chezmoi]\nmanaged_sign="F"\nmodified_sign="m"\nmodified={fg="#112233"}\n',
    )
    write(
        t.root / "config/theme.toml",
        '[flavor]\ndark="fixture"\nlight="fixture"\n[chezmoi]\nmanaged_sign="界"\n',
    )
    t.key("Y", settle=0)

    def themed(capture):
        return (
            screen.linemode(capture, "local", 4) == "界mm "
            and screen.linemode(capture, "source", 4) == "界 m "
        )

    capture = t.wait_screen(themed, "theme override and flavor fallback")
    local_suffix = screen.linemode(capture, "local", 4)
    source_suffix = screen.linemode(capture, "source", 4)
    assert screen.cell_width(local_suffix) == screen.cell_width(source_suffix) == 5
    colored = screen.row(t.capture(ansi=True), "source", ansi=True)
    assert colored is not None and "38;2;17;34;51" in colored, colored
    t.quit()
    clean_logs(t)


def git_coexistence(t):
    t.start(settle=0)

    def ordered(capture):
        value = screen.row(capture, "local")
        return (
            value is not None
            and "G " in value
            and "CMM " in value
            and value.index("G ") < value.index("CMM ")
        )

    t.wait_screen(ordered, "git.yazi before chezmoi.yazi on the same row")
    t.quit()
    clean_logs(t)


SCENARIOS = {
    "status-refresh": status_refresh,
    "navigation": navigation,
    "failure-recovery": failure_recovery,
    "theme-reload": theme_reload,
    "git-coexistence": git_coexistence,
}
DEFAULT_CASES = ["status-refresh", "navigation", "failure-recovery", "theme-reload"]


def version(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def save_artifacts(t, directory, name):
    target = directory / name
    target.mkdir(parents=True, exist_ok=True)
    if t.started and t.alive():
        t.capture()
        t.capture(ansi=True)
    if t.last_capture:
        write(target / "screen.txt", t.last_capture)
    if t.last_capture_ansi:
        write(target / "screen-ansi.txt", t.last_capture_ansi)
    write(target / "yazi.log", t.logs())
    metadata = {
        "fixture": str(t.root),
        "versions": [
            version(["yazi", "-V"]),
            version(["chezmoi", "--version"]),
            version(["tmux", "-V"]),
        ],
    }
    write(target / "metadata.json", json.dumps(metadata, indent=2) + "\n")


def run_case(name, args):
    git_plugin = args.git_plugin if name == "git-coexistence" else None
    t = Runtime(git_plugin, instrument=False, probe=False, keep=args.keep)
    failed = False
    try:
        baseline(t)
        SCENARIOS[name](t)
        print(f"PASS {name}")
    except Exception:
        failed = True
        print(f"FAIL {name}", file=sys.stderr)
        traceback.print_exc()
        if t.started and t.alive():
            print(t.capture(), file=sys.stderr)
        logs = t.logs()
        if logs:
            print(logs, file=sys.stderr)
        if args.artifacts:
            try:
                save_artifacts(t, args.artifacts, name)
            except Exception:
                print("Failed to save E2E artifacts", file=sys.stderr)
                traceback.print_exc()
    finally:
        try:
            t.close()
        except Exception:
            failed = True
            print(f"FAIL {name} cleanup", file=sys.stderr)
            traceback.print_exc()
    return not failed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--smoke", action="store_true", help="Run the PR smoke scenario")
    selection.add_argument(
        "--case",
        action="append",
        choices=SCENARIOS,
        dest="cases",
        help="Run only this scenario; repeat to select more",
    )
    parser.add_argument(
        "--git-plugin",
        type=Path,
        help="Add the git.yazi coexistence scenario using this checkout",
    )
    parser.add_argument("--keep", action="store_true", help="Retain every fixture")
    parser.add_argument(
        "--artifacts", type=Path, help="Save failure artifacts below this directory"
    )
    args = parser.parse_args()

    cases = ["status-refresh"] if args.smoke else list(args.cases or DEFAULT_CASES)
    if args.git_plugin and "git-coexistence" not in cases:
        cases.append("git-coexistence")
    if "git-coexistence" in cases and not args.git_plugin:
        parser.error("--case git-coexistence requires --git-plugin")

    results = [run_case(name, args) for name in cases]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
