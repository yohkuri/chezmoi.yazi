#!/usr/bin/env -S uv run --locked
"""Real Yazi/chezmoi checks in an isolated fixture."""
import argparse
import json
import time
import subprocess
from support import baseline, fixture, read, write
from action_cases import commands, extended, configure, finish, confirm


def test(t, git_plugin):
    def source(name, text):
        write(t.source / name, text)

    def record(s, name):
        return (s.get("records") or {}).get(str(t.dest / name), {})

    def has(name, key, value):
        return lambda s: record(s, name).get(key) == value

    baseline(t)
    source("new\nline", "newline edit\n")
    sentinel = t.root / "script-ran"
    assert " R " in t.chezmoi("status", "--path-style=absolute", t.dest / ".config")
    identity = t.root / "age-identity"
    # Public age manual key, only for disposable test data:
    # https://github.com/FiloSottile/age/blob/main/doc/age.1.html
    write(identity, "AGE-SECRET-KEY-1KTYK6RVLN5TAPE7VF6FQQSKZ9HWWCDSKUGXXNUQDWZ7XXT5YK5LSF3UTKQ\n")
    identity.chmod(0o600)
    recipient = "age1gde3ncmahlqd9gg50tanl99r960llztrhfapnmx853s4tjum03uqfssgdh"
    write(t.cfg, f'encryption="age"\nuseBuiltinAge=true\n[age]\nidentity={json.dumps(str(identity))}\nrecipient="{recipient}"\n')
    plain = t.root / "plaintext"
    write(plain, "encrypted fixture\n")
    source("encrypted_secret.age", t.chezmoi("encrypt", plain))
    write(t.dest / "secret", "different\n")
    t.process_tests()
    t.start()
    result = t.wait(has("local", "xy", "MM"))
    for name, xy in {"clean": "  ", "source": " M", "remove-me": " D",
                     "new\nline": " M", "link": "  ", "secret": " M"}.items():
        assert record(result, name)["xy"] == xy, name
    for name in ["unmanaged", "ignored"]:
        assert record(result, name)["membership"] == "unmanaged"
    for name in [".config", ".exact"]:
        assert record(result, name)["summary"] == "changed"
    assert not sentinel.exists(), "Status must not execute apply scripts"
    print("PASS real fetcher, XY, unmanaged, missing descendant summary")
    screen = t.capture()
    assert all(sign in screen for sign in ["CMM", "C M", "C  *"]), screen
    print("PASS actual terminal rendering")
    if git_plugin:
        deadline = time.monotonic() + 3
        while "G " not in t.capture() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert any("G " in line and "CMM" in line and line.index("G ") < line.index("CMM")
                   for line in t.capture().splitlines()), t.capture()
        print("PASS git.yazi coexistence and linemode ordering")
    identity.rename(t.root / "hidden-identity")
    t.refresh(has("secret", "failed", True))
    (t.root / "hidden-identity").rename(identity)
    t.refresh(has("secret", "xy", " M"))
    print("PASS pending script stays unexecuted, encrypted status, missing identity and recovery")
    source("local", read(t.dest / "local"))
    t.refresh(has("local", "xy", "  "))
    assert "CMM" not in t.capture()
    print("PASS manual refresh clears resolved changes")
    # Exercise recursive batches after the exceptional-filename fallback.
    (t.source / "new\nline").unlink()
    (t.source / "carriage\rreturn").unlink()
    (t.source / "bad").rename(t.source / "bad.tmpl")
    source("bad.tmpl", "{{ .missing.field }}")
    result = t.refresh(has("bad", "failed", True))
    assert record(result, "clean")["xy"] == "  "
    assert "C!!" in t.capture()
    source("bad.tmpl", "original\n")
    t.refresh(has("bad", "xy", "  "))
    print("PASS broken template isolation, failure rendering, recovery")
    assert "--recursive=true" in read(t.calls)
    source("dot_config/broken.tmpl", "{{ .missing.field }}")
    result = t.refresh(has(".config", "partial", True))
    assert record(result, ".config")["xy"] == "  "
    (t.source / "dot_config/broken.tmpl").unlink()
    t.key("N")
    t.wait(lambda s: s["cwd"] == str(t.dest / ".config"))
    source("source", read(t.dest / "source"))
    t.key("B")
    t.wait(lambda s: s["cwd"] == str(t.dest) and record(s, "source").get("xy") == "  ")
    t.key("G")
    t.wait(lambda s: s["cwd"] == str(t.dest / ".config"))
    t.key("H")
    t.wait(lambda s: s["cwd"] == str(t.dest) and record(s, "source").get("xy") == "  ")
    print("PASS partial summaries, directory revisit, tab switching")
    write(t.control, "fail-managed")
    t.refresh(has("clean", "membership", "error"))
    t.control.unlink()
    t.refresh(has("clean", "xy", "  "))
    source("unmanaged", "other\n")
    t.refresh(has("unmanaged", "membership", "managed"))
    (t.source / "unmanaged").unlink()
    t.refresh(has("unmanaged", "membership", "unmanaged"))
    print("PASS failed membership, recovery, externally added/forgotten paths")
    write(t.control, "slow")
    t.key("R")
    deadline = time.monotonic() + 4
    while not t.barrier.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert t.barrier.exists(), "Slow status never started"
    epoch = t.snapshot()["epoch"]
    source("source", "new generation\n")
    t.control.unlink()
    t.key("R")
    deadline = time.monotonic() + 6
    finished = False
    while time.monotonic() < deadline:
        result = t.snapshot()
        r = record(result, "source")
        assert result["epoch"] > epoch
        assert r.get("xy") != "  ", "Old generation published after refresh"
        if r.get("xy") == " M" and not result["running"]:
            finished = True
            break
    assert finished, "New generation did not finish"
    calls = read(t.calls)
    time.sleep(0.7)
    assert read(t.calls) == calls, "Stationary view unexpectedly polled chezmoi"
    print("PASS generation cancellation and absence of periodic polling")
    for mode in ["silent", "closed", "partial", "stderr"]:
        t.check_process(mode)
    print("PASS bounded process lifetime, closed stdout, partial output, stderr backpressure")
    source("source", "again\n")
    t.refresh(has("source", "xy", " M"))
    flavor = t.root / "config/flavors/fixture.yazi"
    flavor.mkdir(parents=True)
    write(flavor / "tmtheme.xml", '<?xml version="1.0"?><plist version="1.0"><dict><key>name</key><string>test</string><key>settings</key><array/></dict></plist>')
    write(flavor / "flavor.toml", '[chezmoi]\nmanaged_sign="F"\nmodified_sign="m"\nmodified={fg="#112233"}\n')
    write(t.root / "config/theme.toml", '[flavor]\ndark="fixture"\nlight="fixture"\n[chezmoi]\nmanaged_sign="界"\n')
    before = t.snapshot()["epoch"]
    t.key("Y")
    result = t.wait(lambda s: s["signs"]["managed"] == "界")
    assert result["signs"]["modified"] == "m", result["signs"]
    assert result["epoch"] == before, "Theme reload must not invalidate status"
    assert "界 m" in t.capture(), t.capture()
    assert "38;2;17;34;51" in t.tmux("capture-pane", "-e", "-p", "-t", "test")
    print("PASS real flavor fallback, theme override/reload, wide signs, RGB style")
    logs = t.logs()
    assert "Error when running" not in logs and "runtime error:" not in logs, logs
    assert not sentinel.exists(), "Apply script ran during a later query"


def action_coordination(t):
    baseline(t)
    configure(t)
    t.start()
    instance_id = t.snapshot()["instance"]

    def emit(name, *args):
        result = subprocess.run(["ya", "emit-to", instance_id, name, *args],
                                env=t.env, cwd=t.root, capture_output=True, timeout=5)
        assert result.returncode == 0, result.stderr

    def snapshot():
        t.report.unlink(missing_ok=True)
        emit("plugin", "probe")
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                return json.loads(read(t.report))
            except (FileNotFoundError, json.JSONDecodeError):
                time.sleep(0.03)
        raise AssertionError("No remote probe response")

    # Trigger an action while an obsolete status acquisition is still running.
    t.key("3")
    write(t.control, "slow")
    t.key("R")
    deadline = time.monotonic() + 4
    while not t.barrier.exists() and time.monotonic() < deadline:
        time.sleep(0.03)
    assert t.barrier.exists()
    t.key("p")
    t.wait_screen(lambda s: "Press Enter to return" in s, "diff with action lock held")
    state = snapshot()
    assert state["action_busy"] and not state["running"]
    before = read(t.calls)
    emit("plugin", "chezmoi", "add")
    emit("plugin", "chezmoi", "refresh")
    time.sleep(0.25)
    assert read(t.calls) == before, "Concurrent action/refresh started a subprocess"
    t.control.unlink()
    finish(t, next_confirm=True)
    confirm(t, False)
    t.wait(lambda s: not s["action_busy"] and not s["running"])
    # Freeze selection before menu input, even if DDS moves the hover elsewhere.
    t.key("2"); t.key("C")
    t.wait_screen(lambda s: "Add options" in s, "menu snapshot")
    emit("reveal", str(t.dest / "source"))
    t.key("a"); finish(t)
    assert read(t.source / "unmanaged") == "other\n"
    assert read(t.source / "source") == "source edit\n"
    # A selection in another directory remains part of the tab's selection.
    t.key("S"); t.key("1"); t.key("s")
    emit("reveal", str(t.dest / ".exact/keep"))
    t.wait(lambda s: s["cwd"] == str(t.dest / ".exact"))
    t.key("s"); t.key("r"); confirm(t); finish(t)
    calls = [json.loads(line) for line in read(t.calls).splitlines()]
    readd = [args for args in calls if "re-add" in args and "--no-tty" not in args][-1]
    assert str(t.dest / "clean") in readd and str(t.dest / ".exact/keep") in readd
    t.wait(lambda s: not s["action_busy"] and not s["running"])
    assert "runtime error:" not in t.logs(), t.logs()
    print("PASS action coordination: stale worker, operation lock, menu snapshot, cross-directory selection")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git-plugin")
    args = parser.parse_args()
    with fixture(args.git_plugin) as instance:
        test(instance, args.git_plugin)
    with fixture(args.git_plugin) as instance:
        baseline(instance)
        commands(instance)
    with fixture(args.git_plugin) as instance:
        baseline(instance)
        extended(instance)
    with fixture(args.git_plugin) as instance:
        action_coordination(instance)
