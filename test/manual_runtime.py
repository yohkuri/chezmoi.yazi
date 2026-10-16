#!/usr/bin/env -S uv run --locked
"""Real-terminal checks for the guided manual session (private tmux only)."""
import json
from pathlib import Path
import time
from action_cases import confirm, enter, finish
from manual import configure_guide, install_guide
from manual_backend import current, load, remove_attempts, save, transition
from manual_cases import CASES
from support import REPO, fixture, read, write, stop


def control(t, key, settle=0.3):
    t.key("W")
    t.wait_screen(lambda s: "Next step" in s, "guide controls")
    t.key(key, settle=settle)


def choose_case(t, number, settle=0.3):
    control(t, "j", settle=settle)
    t.wait_screen(lambda s: "Case number" in s, "case chooser")
    t.key(str(number))
    enter(t)
    t.wait_screen(lambda s: f"{number}/{len(CASES)} " in s, "new case")


def test(t):
    write(t.root / "manual.json", json.dumps(dict(version=1, root=str(t.root), repo=str(REPO))))
    write(t.root / "baseline-theme.toml", "")
    v = configure_guide(t, None)
    install_guide(t, v, None)
    t.dest = Path(v["opts"]["destination"])
    t.start()

    def state():
        return load(t.root)[1]

    def wait_state(predicate, description, timeout=10):
        deadline = time.monotonic() + timeout
        latest = None
        while time.monotonic() < deadline:
            latest = state()
            if predicate(latest):
                return latest
            time.sleep(0.05)
        raise AssertionError(f"Timed out waiting for {description}: {latest}\n{t.capture()}")

    last_pass = float("-inf")

    def send_pass():
        nonlocal last_pass
        remaining = 0.8 - (time.monotonic() - last_pass)
        if remaining > 0:
            time.sleep(remaining)
        t.key("P")
        last_pass = time.monotonic()

    def accept():
        before = state()
        active, index = before["active"], current(before)["step"]
        send_pass()
        wait_state(lambda s: s["attempts"][active]["steps"][index]["status"] == "PASS", "single-key PASS")
        after = wait_state(lambda s: (s["active"], current(s)["step"]) != (active, index)
                           or s.get("finished"), "single-key advancement")
        attempt = current(after)
        title = f'{attempt["case"] + 1}/{len(CASES)} {CASES[attempt["case"]]["title"]} - step {attempt["step"] + 1}/'
        t.wait_screen(lambda s: ("Walk complete" if after.get("finished") else title) in s
                      and "Preparing/checking..." not in s, "guide ready after advancement")
        return after["attempts"][active]

    def jump(key):
        number = next(i + 1 for i, case in enumerate(CASES) if case["key"] == key)
        choose_case(t, number)
        root = Path(state()["attempts"][-1]["root"])
        t.wait(lambda s: s["cwd"] == str(root / "dest") and not s["running"])
        return root

    t.wait_screen(lambda s: "P: PASS/check/next" in s and "CMM" in s, "initial guide and rows")
    control(t, "n")
    assert state()["attempts"][0]["step"] == 0, "Unanswered observation advanced"
    t.tmux("send-keys", "-t", "test", "P", "P", "P")
    last_pass = time.monotonic()
    t.wait_screen(lambda s: "step 2/2" in s, "single-key next step")
    assert state()["attempts"][0]["steps"][0]["status"] == "PASS"
    assert state()["attempts"][0]["steps"][1]["visual"] == "unanswered", "Repeated P answered the next step"
    t.tmux("resize-window", "-t", "test", "-x", "80", "-y", "30")
    t.wait_screen(lambda s: "Inside .config: no files" in s and "Back at root" in " ".join(s.split())
                  and "P: PASS/check/next" in s, "wrapped concrete expectations")
    t.tmux("resize-window", "-t", "test", "-x", "140", "-y", "40")
    original = Path(v["root"])
    control(t, "r")
    t.wait_screen(lambda s: "step 1/2" in s, "fresh restart")
    assert Path(state()["attempts"][-1]["root"]) != original and original.exists()
    control(t, "h")
    assert "W: controls" not in t.capture(), "Hidden guide still rendered"
    control(t, "h")
    t.wait_screen(lambda s: "W: controls" in s, "guide restored")
    t.tmux("resize-window", "-t", "test", "-x", "80", "-y", "18")
    t.wait_screen(lambda s: "W: controls" in s, "compact guide")
    t.tmux("resize-window", "-t", "test", "-x", "140", "-y", "40")
    t.wait_screen(lambda s: "W: controls" in s, "full guide after resize")
    jump("names")
    accept()
    t.wait_screen(lambda s: "step 2/2" in s, "last names step")
    control(t, "s")
    t.wait_screen(lambda s: "Observation / skip reason" in s, "skip reason")
    enter(t)
    t.wait_screen(lambda s: "Visual: SKIP" in s, "recorded skip")
    control(t, "d")
    t.wait_screen(lambda s: "Enter: next | b: back | q: return to Yazi" in s, "skipped step diagnostics")
    t.key("q"); enter(t)
    t.wait_screen(lambda s: "Visual: SKIP" in s, "skip retained after diagnostics")
    control(t, "n")
    t.wait_screen(lambda s: "3/24 Manual refresh" in s, "next case after skipped step")
    assert state()["results"][1] == "SKIP", state()["results"]
    jump("git")
    control(t, "n")
    t.wait_screen(lambda s: "Walk complete" in s and "SKIP:" in s, "completed walk")
    assert "Do:" not in t.capture() and "Expect:" not in t.capture(), "Stale instructions after completion"
    control(t, "r")
    t.wait_screen(lambda s: "24/24 git.yazi coexistence" in s and "Walk complete" not in s, "reopened last case")
    assert not state()["finished"]
    control(t, "n")
    t.wait_screen(lambda s: "Walk complete" in s, "completed restarted walk")
    root = jump("refresh")
    assert not state()["finished"]
    print("PASS guide: SKIP survives diagnostics/case change; restart and jump restore case titles after completion")
    accept()
    assert read(root / "source/local") == "local edit\n"
    time.sleep(1)
    held = t.snapshot()["records"][str(root / "dest/local")]
    assert held["xy"] == "MM", held
    send_pass()
    assert state()["attempts"][-1]["step"] == 1, "Failed refresh verification advanced"
    assert state()["attempts"][-1]["steps"][1]["status"] == "FAIL"
    t.refresh(lambda s: (s.get("records") or {}).get(str(root / "dest/local"), {}).get("xy") == "  ")
    accept()
    t.refresh(lambda s: (s.get("records") or {}).get(str(root / "dest/local"), {}).get("xy") == "MM")
    accept()
    print("PASS guide: single-key progress, repeated-key guard, failed-check gate, held cache and real refresh")
    root = jump("visual-unset")
    t.key("1"); t.key(" "); t.key("j"); t.key(" "); t.key("j"); t.key(" ")
    t.key("1"); t.key("V"); t.key("j")
    control(t, "h")  # Opening/closing controls must not escape visual mode.
    t.key("a")
    finish(t)
    t.wait(lambda s: not s["action_busy"])
    assert (root / "source/range-c").exists()
    assert not (root / "source/range-a").exists() and not (root / "source/range-b").exists()
    control(t, "h")
    print("PASS guide controls preserve visual unset selection for real actions")
    jump("theme")
    accept(); t.key("Y")
    accept()
    t.key("Y"); accept()
    root = jump("edit")
    t.key("6"); t.key("e")
    t.wait_screen(lambda s: "New source content" in s, "fixture editor")
    screen = t.capture()
    assert "Running (argv):" in screen and "--apply=false" in screen and "--watch=false" in screen, screen
    t.key("edited by fixture"); enter(t)
    finish(t)
    history = [json.loads(line) for line in read(root / "state/instrument/actions.jsonl").splitlines()]
    assert len(history) == 1 and history[0]["exit_code"] == 0 and "edit" in history[0]["argv"], history
    accept()
    jump("encryption")
    t.key("7"); t.key("z"); finish(t); accept()
    jump("template-add")
    t.key("7"); t.key("t"); finish(t); accept()
    root = jump("edit-apply")
    t.key("6"); t.key("E")
    t.wait_screen(lambda s: "New source content" in s, "edit-and-apply editor")
    t.key("edited by fixture"); enter(t)
    finish(t, next_command=True); finish(t, next_confirm=True); confirm(t, False)
    history = [json.loads(line) for line in read(root / "state/instrument/actions.jsonl").splitlines()]
    assert len(history) == 2 and "edit" in history[0]["argv"] and "diff" in history[1]["argv"], history
    assert all(item["exit_code"] == 0 for item in history), history
    accept()
    jump("mixed")
    t.key("8"); t.key(" "); t.key("7"); t.key(" "); t.key("e")
    t.wait_screen(lambda s: "Not managed" in s, "mixed Edit rejection")
    t.wait(lambda s: not s["action_busy"] and not s["running"])
    accept()
    t.tmux("send-keys", "-t", "test", "Escape")
    time.sleep(0.3)  # Let the terminal decode Escape before the digit shortcut.
    t.key("9"); t.key("e")
    t.wait_screen(lambda s: "Select files inside" in s, "standard Escape cleared selection")
    t.wait(lambda s: not s["action_busy"] and not s["running"])
    accept()
    jump("navigation")
    t.key("G"); t.key("H")
    root = jump("confirmation")
    # Changing cases must dispose of old tabs, and select every exact target.
    t.key("4", settle=0.8); t.key("x")
    t.wait_screen(lambda s: "Continue?" in s and "Targets: 6" in s, "long target selection")
    confirm(t, yes=False)
    assert all((root / "dest" / name).exists() for name in json.loads(read(root / "long.json")))
    print("PASS guide: theme epoch, command argv/history, cancelled apply, standard Escape, encryption and exact targets")
    jump("source-protection")
    t.key("5"); t.key("x")
    t.wait_screen(lambda s: "contains the source" in s, "source-ancestor rejection")
    previous = state()
    theme = t.root / "baseline-theme.toml"
    original_theme = read(theme)
    theme.unlink()
    try:
        control(t, "r")
        number = current(previous)["case"] + 1
        t.wait_screen(lambda s: f"Could not prepare case {number}, step 1" in s, "preparation failure notification")
        failed = state()
        assert failed["attempts"] == previous["attempts"], failed
        assert failed["results"] == previous["results"], failed
        error = failed["preparation_errors"][-1]
        assert error["operation"] == "restart" and error["case"] == number - 1 and error["step"] == 0, error
    finally:
        write(theme, original_theme)
    control(t, "d")
    t.wait_screen(lambda s: "Enter: next | b: back | q: return to Yazi" in s, "same-terminal details")
    deadline = time.monotonic() + 5
    while "PREPARATION ERRORS" not in t.capture():
        assert time.monotonic() < deadline, t.capture()
        enter(t)
    assert "restart: case" in t.capture(), t.capture()
    t.key("q"); enter(t)
    t.wait_screen(lambda s: "W: controls" in s, "return from details")
    t.key("q")
    t.wait_screen(lambda s: "Save, retain fixtures and exit" in s, "finish menu")
    t.key("k")
    time.sleep(0.3)
    assert state()["exit"]["keep"] is True
    print("PASS guide: source protection, preparation failure attribution, foreground details and saved exit choice")


def foreground_launcher():
    before = set((REPO / ".dev/manual-runs").glob("*/results.json"))
    with fixture() as t:
        t.tmux("new-session", "-d", "-s", "test", "-x", "140", "-y", "40",
               "-c", str(REPO), str(REPO / "test/manual.py"))
        t.started = True
        t.tmux("set-option", "-w", "remain-on-exit", "on")
        t.wait_screen(lambda s: "P: PASS/check/next" in s and "CMM" in s, "foreground launcher")
        number = next(i + 1 for i, case in enumerate(CASES) if case["key"] == "interrupt")
        choose_case(t, number, settle=0.1)
        t.wait_screen(lambda s: f"{number}/{len(CASES)} Editor interruption" in s, "launcher interrupt case")
        for _ in range(2):
            t.key("6", settle=0.5); t.key("E")
            t.wait_screen(lambda s: "New source content" in s, "launcher fixture editor")
            t.tmux("send-keys", "-t", "test", "C-c")
            finish(t, success=False)
            t.wait_screen(lambda s: "W: controls" in s, "launcher survives editor Ctrl-C")
        t.key("P", settle=0.1)
        t.wait_screen(lambda s: "18/24 Diff and pending script" in s, "single-key PASS after interruption")
        t.key("q")
        t.wait_screen(lambda s: "Save and exit; clean fixtures" in s, "launcher finish menu")
        t.key("c")
        t.wait_screen(lambda s: "Results:" in s, "archived launcher report")
    reports = set((REPO / ".dev/manual-runs").glob("*/results.json")) - before
    assert len(reports) == 1, reports
    report = json.loads(read(next(iter(reports))))
    assert report["results"][number - 1] == "PASS", report["attempts"][-1]
    assert not Path(report["session"]).exists()
    assert all(not Path(a["root"]).exists() for a in report["attempts"])
    print("PASS foreground launcher: repeated editor Ctrl-C returns to usable Yazi; unchanged files, archive and cleanup")


def resumed_refresh():
    """Resume both epoch-gated refresh steps through the foreground launcher."""
    for step in [1, 2]:
        with fixture() as t:
            write(t.root / "manual.json", json.dumps(dict(version=1, root=str(t.root), repo=str(REPO))))
            write(t.root / "baseline-theme.toml", "")
            try:
                value = configure_guide(t, None)
                index = next(i for i, case in enumerate(CASES) if case["key"] == "refresh")
                value = transition(t.root, "jump", dict(token=value["token"], index=index))
                for _ in range(step):
                    value = transition(t.root, "skip", dict(token=value["token"]))
                    value = transition(t.root, "next", dict(token=value["token"]))
                saved = load(t.root)[1]
                active = saved["active"]
                current(saved)["epoch_before"] = 50  # The previous Yazi process had its own epoch.
                save(t.root, saved)
                root = Path(value["root"])
                t.tmux("new-session", "-d", "-s", "test", "-x", "140", "-y", "40",
                       "-c", str(REPO), str(REPO / "test/manual.py"), "open", str(t.root))
                t.started = True
                t.tmux("set-option", "-w", "remain-on-exit", "on")
                title = f"3/24 Manual refresh - step {step + 1}/3"
                t.wait_screen(lambda s: title in s and "P: PASS/check/next" in s, "resumed refresh ready")
                snapshot = t.wait(lambda s: s["cwd"] == str(root / "dest") and not s["running"])
                t.key("P")
                t.wait_screen(lambda s: "Checks failed; staying" in s and "P: PASS/check/next" in s,
                              "resumed refresh requires R")
                attempt = current(load(t.root)[1])
                assert attempt["step"] == step and attempt["steps"][step]["status"] == "FAIL", attempt
                t.refresh(lambda s: not s["running"])
                time.sleep(0.8)  # Separate the two PASS attempts from the repeat-key guard.
                t.key("P")
                expected = "step 3/3" if step == 1 else "4/24 Membership discovery"
                t.wait_screen(lambda s: expected in s and "P: PASS/check/next" in s, "resumed refresh advances after R")
                attempt = load(t.root)[1]["attempts"][active]
                assert attempt["steps"][step]["status"] == "PASS", attempt
                assert attempt["steps"][step]["visual"] == "PASS", attempt
                # Step 2 advances within the attempt and replaces its baseline for step 3.
                if step == 2:
                    assert attempt["epoch_before"] == snapshot["epoch"], attempt
                t.key("q")
                t.wait_screen(lambda s: "Save, retain fixtures and exit" in s, "resumed finish menu")
                t.key("k")
                t.wait_screen(lambda s: "Results:" in s, "resumed report archived")
            finally:
                if (t.root / "walk.json").exists() and not t.keep:
                    stop(t.root)
                    t.started = False
                    remove_attempts(load(t.root)[1])
    print("PASS resumed refresh: steps 2 and 3 reject PASS before R and advance after R")


def backend_paths():
    """Exercise real fixture setup and separate CLI processes, without git UI."""
    import sys
    from support import run
    with fixture(probe=False, instrument=False) as t:
        write(t.root / "manual.json", json.dumps(dict(version=1, root=str(t.root), repo=str(REPO))))
        write(t.root / "baseline-theme.toml", "")
        plugin = t.root / "git.yazi"
        plugin.mkdir()
        write(plugin / "main.lua", "return { setup = function() end }\n")
        code = ('import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); '
                'from manual_backend import initialize; initialize(Path(sys.argv[2]), sys.argv[3])')
        try:
            run([sys.executable, "-c", code, str(REPO / "test"), str(t.root), "git.yazi"], cwd=t.root, env=t.env)
            value = load(t.root)[1]
            assert value["git_plugin"] == str(plugin), value["git_plugin"]
            token = "0:0"
            for operation in ["restart", "jump"]:
                # Yazi's backend cwd differs from the original invocation cwd.
                result = json.loads(run([sys.executable, str(REPO / "test/manual_backend.py"), str(t.root), operation,
                                         json.dumps(dict(token=token, index=1))], cwd=t.dest, env=t.env))
                assert result["result"]["status"] == "NOT RUN", result
                assert (Path(result["root"]) / "config/plugins/git.yazi").resolve() == plugin
                token = result["token"]
        finally:
            if (t.root / "walk.json").exists():
                remove_attempts(load(t.root)[1])
    print("PASS backend CLI: relative git plugin persists across cwd changes, restart and jump")


def main():
    backend_paths()
    with fixture() as t:
        try:
            test(t)
        finally:
            if (t.root / "walk.json").exists() and not t.keep:
                stop(t.root)
                t.started = False
                remove_attempts(load(t.root)[1])

    foreground_launcher()
    resumed_refresh()


if __name__ == "__main__":
    main()
