#!/usr/bin/env -S uv run --locked
"""Real-terminal checks for the guided manual session (private tmux only)."""
import json
from pathlib import Path
import time
from action_cases import confirm, enter, finish, native_confirm
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


def assert_mode_colors(t, mode, background):
    t.wait_screen(lambda s: f" {mode} " in s, f"{mode} mode status bar")
    line = next(line for line in t.capture(ansi=True).splitlines() if f" {mode} " in line)
    assert "38;2;30;30;46" in line and f"48;2;{background}" in line, line


def test(t):
    write(t.root / "manual.json", json.dumps(dict(version=1, root=str(t.root), repo=str(REPO))))
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

    last_verdict = float("-inf")

    def send_verdict(key="P", settle=0.1):
        nonlocal last_verdict
        remaining = 0.8 - (time.monotonic() - last_verdict)
        if remaining > 0:
            time.sleep(remaining)
        t.key(key, settle=settle)
        last_verdict = time.monotonic()

    def accept():
        before = state()
        active, index = before["active"], current(before)["step"]
        send_verdict()
        wait_state(lambda s: s["attempts"][active]["steps"][index]["status"] == "PASS", "single-key PASS")
        after = wait_state(lambda s: (s["active"], current(s)["step"]) != (active, index)
                           or s.get("finished"), "single-key advancement")
        attempt = current(after)
        title = f'{attempt["case"] + 1}/{len(CASES)} {CASES[attempt["case"]]["title"]} - step {attempt["step"] + 1}/'
        t.wait_screen(lambda s: ("Walk complete" if after.get("finished") else title) in s
                      and "Preparing/checking..." not in s, "guide ready after advancement")
        return after["attempts"][active]

    def jump(key):
        before = state()["active"]
        number = next(i + 1 for i, case in enumerate(CASES) if case["key"] == key)
        choose_case(t, number)
        after = wait_state(lambda s: s["active"] != before, "fresh case after jump")
        root = Path(current(after)["root"])
        t.wait_screen(lambda s: f"{number}/{len(CASES)} " in s and "Preparing/checking..." not in s, "guide ready after jump")
        t.wait(lambda s: s["cwd"] == str(root / "dest") and not s["running"])
        return root

    t.wait_screen(lambda s: "P: PASS/check/next" in s and "S: SKIP/next" in s and "CMM" in s, "initial guide and rows")
    for light, report in [(True, 2), (False, 1)]:
        t.tmux("send-keys", "-t", "test", "-l", f"\x1b[?997;{report}n")
        t.wait(lambda s: s.get("light") is light)
        t.key("Y")
        assert_mode_colors(t, "NOR", "137;180;250")
    assert_mode_colors(t, "NOR", "137;180;250")
    t.key("v")
    assert_mode_colors(t, "SEL", "148;226;213")
    t.tmux("send-keys", "-t", "test", "Escape")
    assert_mode_colors(t, "NOR", "137;180;250")
    t.key("V")
    assert_mode_colors(t, "UNS", "242;205;205")
    t.tmux("send-keys", "-t", "test", "Escape")
    assert_mode_colors(t, "NOR", "137;180;250")
    t.tmux("send-keys", "-t", "test", "Escape")
    time.sleep(0.3)  # Decode the final Escape before the following guide key.
    print("PASS manual status colors: dark/light terminal reports, normal/select/unset modes")
    control(t, "n")
    assert state()["attempts"][0]["step"] == 0, "Unanswered observation advanced"
    t.tmux("send-keys", "-t", "test", "P", "P", "P")
    last_verdict = time.monotonic()
    t.wait_screen(lambda s: "step 2/2" in s, "single-key next step")
    assert state()["attempts"][0]["steps"][0]["status"] == "PASS"
    assert state()["attempts"][0]["steps"][1]["visual"] == "unanswered", "Repeated P answered the next step"
    t.tmux("resize-window", "-t", "test", "-x", "80", "-y", "30")
    screen = t.wait_screen(lambda s: "Narrow and enlarge" in " ".join(s.split()) and "Use W/d" in " ".join(s.split())
                           and "P: PASS/check/next" in s, "wrapped ordered instructions")
    text = " ".join(screen.split())
    assert text.index("hide the guide") < text.index("Narrow and enlarge") < text.index("restore the guide"), screen
    assert all(label not in screen for label in ["Do:", "Expect:", "Command:"]), screen
    t.tmux("resize-window", "-t", "test", "-x", "140", "-y", "40")
    original = Path(v["root"])
    control(t, "r")
    t.wait_screen(lambda s: "step 1/2" in s and "Preparing/checking..." not in s, "fresh restart")
    assert Path(state()["attempts"][-1]["root"]) != original and original.exists()
    active = state()["active"]
    send_verdict("S", settle=0)
    skipped = wait_state(lambda s: current(s)["step"] == 1, "single-key SKIP within case")
    assert skipped["attempts"][active]["steps"][0]["status"] == "SKIP", skipped
    assert "files" not in skipped["attempts"][active]["steps"][0], "SKIP ran checks"
    t.tmux("send-keys", "-t", "test", "P", "S", "S")
    last_verdict = time.monotonic()
    t.wait_screen(lambda s: "step 2/2" in s and "Preparing/checking..." not in s, "guide ready after SKIP")
    assert current(state())["steps"][1]["visual"] == "unanswered", "Repeated or mixed verdict keys answered the next step"
    send_verdict("S")
    t.wait_screen(lambda s: "2/12 Warnings" in s and "Preparing/checking..." not in s, "single-key SKIP to next case")
    assert state()["results"][0] == "SKIP"
    assert current(state())["steps"][0]["visual"] == "unanswered"
    print("PASS guide: single-key SKIP within/across cases, no checks/reason prompt, shared verdict-key guard")
    control(t, "h")
    assert "W: controls" not in t.capture(), "Hidden guide still rendered"
    control(t, "h")
    t.wait_screen(lambda s: "W: controls" in s, "guide restored")
    t.tmux("resize-window", "-t", "test", "-x", "40", "-y", "18")
    t.wait_screen(lambda s: "P: PASS | S: SKIP | W: controls" in s, "compact guide")
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
    t.wait_screen(lambda s: "2/12 Warnings" in s, "next case after skipped step")
    assert state()["results"][0] == "SKIP", state()["results"]
    jump("git")
    control(t, "n")
    t.wait_screen(lambda s: "Walk complete" in s and "SKIP:" in s, "completed walk")
    completed = state()
    t.key("S")
    assert state() == completed, "SKIP changed a completed walk"
    assert CASES[-1]["steps"][0]["instruction"].splitlines()[0] not in t.capture(), "Stale instructions after completion"
    control(t, "r")
    t.wait_screen(lambda s: "12/12 git.yazi coexistence" in s and "Walk complete" not in s, "reopened last case")
    assert not state()["finished"]
    control(t, "n")
    t.wait_screen(lambda s: "Walk complete" in s, "completed restarted walk")
    root = jump("errors")
    assert not state()["finished"]
    t.refresh(lambda s: s["records"].get(str(root / "dest/bad"), {}).get("failed")
              and s["records"].get(str(root / "dest/clean"), {}).get("xy") == "  ")
    accept()
    t.refresh(lambda s: s["records"].get(str(root / "dest/.config"), {}).get("partial"))
    accept()
    t.refresh(lambda s: s["records"].get(str(root / "dest/clean"), {}).get("membership") == "error")
    accept()
    t.refresh(lambda s: s["records"].get(str(root / "dest/bad"), {}).get("xy") == "  "
              and not s["records"].get(str(root / "dest/.config"), {}).get("partial"))
    accept()
    print("PASS guide: consolidated template/membership warnings and recovery")
    root = jump("visual")
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
    assert_mode_colors(t, "NOR", "137;180;250")
    accept()
    t.key("Y"); accept()
    assert_mode_colors(t, "NOR", "137;180;250")
    root = jump("add")
    for key in ["a", "C", "t", "r", "z"]:
        t.key("7"); t.key(key)
        if key == "C":
            t.wait_screen(lambda s: "Re-add" in s, "Re-add menu")
            t.key("r")
        finish(t)
        accept()
    history = [json.loads(line) for line in read(root / "state/instrument/actions.jsonl").splitlines()]
    assert len(history) == 5 and all(item["exit_code"] == 0 for item in history), history
    assert "--template" in history[2]["argv"] and "--encrypt" in history[4]["argv"], history
    print("PASS guide: consolidated Add/Re-add/template/encryption with independent file checks")
    jump("forget")
    t.key("7"); t.key("f"); confirm(t, False); accept()
    t.key("f"); confirm(t); native_confirm(t); finish(t); accept()
    jump("destroy")
    t.key("8"); t.key("x"); confirm(t); native_confirm(t); finish(t); accept()
    print("PASS guide: Forget cancellation/native approval and Destroy native approval")
    root = jump("apply")
    t.key("9"); t.key("d"); finish(t); accept()
    t.key("6"); t.key("p"); finish(t, next_confirm=True); confirm(t, False); accept()
    t.key("9"); t.key("p"); finish(t, next_confirm=True); confirm(t); finish(t); accept()
    print("PASS guide: standalone Diff, cancelled Apply, directory/script preview and approved Apply")
    root = jump("edit")
    send_verdict()
    wait_state(lambda s: current(s)["steps"][0]["status"] == "FAIL", "file-check failure gate")
    assert current(state())["step"] == 0, "Failed file verification advanced"
    t.key("6"); t.key("e")
    t.wait_screen(lambda s: "New source content" in s, "fixture editor")
    screen = t.capture()
    assert "Running (argv):" in screen and "--apply=false" in screen and "--watch=false" in screen, screen
    t.key("edited by fixture"); enter(t)
    finish(t); accept()
    t.key("6"); t.key("E")
    t.wait_screen(lambda s: "New source content" in s, "cancelled Edit and Apply")
    t.key("cancelled edit"); enter(t)
    finish(t, next_command=True); finish(t, next_confirm=True); confirm(t, False); accept()
    t.key("E")
    t.wait_screen(lambda s: "New source content" in s, "approved Edit and Apply")
    t.key("accepted edit"); enter(t)
    finish(t, next_command=True); finish(t, next_confirm=True); confirm(t); finish(t); accept()
    t.key("E")
    t.wait_screen(lambda s: "New source content" in s, "interrupted Edit and Apply")
    t.tmux("send-keys", "-t", "test", "C-c")
    finish(t, success=False); accept()
    history = [json.loads(line) for line in read(root / "state/instrument/actions.jsonl").splitlines()]
    assert [item["argv"][item["argv"].index("--cache") + 2] for item in history] == ["edit", "edit", "diff", "edit", "diff", "apply", "edit"], history
    assert history[-1]["exit_code"] != 0, history
    print("PASS guide: file-check gate, command argv/history, plain Edit, cancelled/approved Edit and Apply, Ctrl-C")
    root = jump("rejections")
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
    t.key("0"); t.key("D")
    t.wait_screen(lambda s: "Non-recursive destroy" in s, "shallow directory rejection")
    t.wait(lambda s: not s["action_busy"] and not s["running"])
    accept()
    t.key("5"); t.key("x")
    t.wait_screen(lambda s: "contains the source" in s, "source-ancestor rejection")
    t.wait(lambda s: not s["action_busy"] and not s["running"])
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
    screen = t.wait_screen(lambda s: "Enter: next | b: back | q: return to Yazi" in s, "same-terminal details")
    assert "Press 5 to move to .local" in " ".join(screen.split()), screen
    assert all(label not in screen for label in ["DO:", "EXPECT:", "COMMAND:"]), screen
    deadline = time.monotonic() + 5
    while "PREPARATION ERRORS" not in t.capture():
        assert time.monotonic() < deadline, t.capture()
        enter(t)
    assert "restart: case" in t.capture(), t.capture()
    t.key("q"); enter(t)
    t.wait_screen(lambda s: "W: controls" in s, "return from details")
    jump("visual")
    t.key("1"); t.key("v"); t.key("j"); t.key("j"); t.key("a")
    t.wait_screen(lambda s: "Targets: 3" in s, "direct three-target confirmation")
    confirm(t); finish(t); accept()
    t.tmux("send-keys", "-t", "test", "Escape")
    time.sleep(0.3)
    t.key("3"); t.key(" "); t.key("h"); t.key("2"); t.key("v"); t.key("j"); t.key("j")
    t.key("C"); t.wait_screen(lambda s: "Add options" in s, "cross-directory Add menu"); t.key("a")
    t.wait_screen(lambda s: "Targets: 4" in s and "outside" in s, "menu cross-directory confirmation")
    confirm(t); finish(t); accept()
    t.key("G"); t.key("H")
    root = jump("confirmation")
    t.key("4", settle=0.8); t.key("x")
    t.wait_screen(lambda s: "Continue?" in s and "Targets: 6" in s, "long target selection")
    confirm(t, yes=False)
    assert all((root / "dest" / name).exists() for name in json.loads(read(root / "long.json")))
    print("PASS guide: direct/menu cross-directory confirmations, extra-tab disposal and exact long targets")
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
        number = next(i + 1 for i, case in enumerate(CASES) if case["key"] == "edit")
        choose_case(t, number, settle=0.1)
        t.wait_screen(lambda s: f"{number}/{len(CASES)} Edit, Edit and Apply" in s, "launcher interrupt case")
        for step in range(1, 4):
            t.key("S")
            t.wait_screen(lambda s: f"step {step + 1}/4" in s and "Preparing/checking..." not in s, "skip to interruption")
            time.sleep(0.8)
        for _ in range(2):
            t.key("6", settle=0.5); t.key("E")
            t.wait_screen(lambda s: "New source content" in s, "launcher fixture editor")
            t.tmux("send-keys", "-t", "test", "C-c")
            finish(t, success=False)
            t.wait_screen(lambda s: "W: controls" in s, "launcher survives editor Ctrl-C")
        t.key("P", settle=0.1)
        t.wait_screen(lambda s: "9/12 Rejected actions" in s, "single-key PASS after interruption")
        t.key("q")
        t.wait_screen(lambda s: "Save and exit; clean fixtures" in s, "launcher finish menu")
        t.key("c")
        t.wait_screen(lambda s: "Results:" in s, "archived launcher report")
    reports = set((REPO / ".dev/manual-runs").glob("*/results.json")) - before
    assert len(reports) == 1, reports
    report = json.loads(read(next(iter(reports))))
    assert report["results"][number - 1] == "SKIP", report["attempts"][-1]
    assert report["attempts"][-2]["steps"][-1]["status"] == "PASS", report["attempts"]
    assert not Path(report["session"]).exists()
    assert all(not Path(a["root"]).exists() for a in report["attempts"])
    print("PASS foreground launcher: repeated editor Ctrl-C returns to usable Yazi; unchanged files, archive and cleanup")


def resumed_theme():
    """Resume both epoch-gated theme steps with the new process baseline."""
    for step in [1, 2]:
        with fixture() as t:
            write(t.root / "manual.json", json.dumps(dict(version=1, root=str(t.root), repo=str(REPO))))
            try:
                value = configure_guide(t, None)
                index = next(i for i, case in enumerate(CASES) if case["key"] == "theme")
                value = transition(t.root, "jump", dict(token=value["token"], index=index))
                for _ in range(step):
                    value = transition(t.root, "skip-next", dict(token=value["token"]))
                saved = load(t.root)[1]
                active = saved["active"]
                current(saved)["epoch_before"] = 50  # The previous process had its own epoch.
                save(t.root, saved)
                root = Path(value["root"])
                write(t.root / "config/keymap.toml", '[[mgr.prepend_keymap]]\non="P"\nrun="plugin manual -- accept"\n')
                t.tmux("new-session", "-d", "-s", "test", "-x", "140", "-y", "40",
                       "-c", str(REPO), str(REPO / "test/manual.py"), "open", str(t.root))
                t.started = True
                t.tmux("set-option", "-w", "remain-on-exit", "on")
                title = f"3/12 Theme, wide signs and colors - step {step + 1}/3"
                t.wait_screen(lambda s: title in s and "P: PASS/check/next" in s, "resumed theme ready")
                snapshot = t.wait(lambda s: s["cwd"] == str(root / "dest") and not s["running"])
                assert current(load(t.root)[1])["epoch_before"] == snapshot["epoch"], snapshot
                assert snapshot["epoch"] != 50
                t.key("Y"); t.key("P")
                expected = "step 3/3" if step == 1 else "4/12 Add, Re-add"
                t.wait_screen(lambda s: expected in s and "P: PASS/check/next" in s, "resumed theme advances after Y")
                attempt = load(t.root)[1]["attempts"][active]
                assert attempt["steps"][step]["status"] == "PASS", attempt
                if step == 1:
                    time.sleep(0.8)
                    t.key("S")
                    t.wait_screen(lambda s: "4/12 Add, Re-add" in s, "resumed session has SKIP binding")
                    assert load(t.root)[1]["attempts"][active]["steps"][2]["status"] == "SKIP"
                t.key("q")
                t.wait_screen(lambda s: "Save, retain fixtures and exit" in s, "resumed finish menu")
                t.key("k")
                t.wait_screen(lambda s: "Results:" in s, "resumed report archived")
            finally:
                if (t.root / "walk.json").exists() and not t.keep:
                    stop(t.root)
                    t.started = False
                    remove_attempts(load(t.root)[1])
    print("PASS resumed theme: steps 2 and 3 replace the old epoch and advance after Y")


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
    resumed_theme()


if __name__ == "__main__":
    main()
