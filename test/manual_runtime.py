#!/usr/bin/env -S uv run --locked
"""Real-terminal checks for the guided manual session (private tmux only)."""
import json
from pathlib import Path
import time
from action_cases import confirm, enter, finish
from manual import configure_guide
from manual_backend import load
from manual_cases import CASES
from support import REPO, fixture, write, owned, stop


def test(t):
    write(t.root / "manual.json", json.dumps(dict(version=1, root=str(t.root), repo=str(REPO))))
    write(t.root / "baseline-theme.toml", "")
    v = configure_guide(t, None)
    t.dest = Path(v["opts"]["destination"])
    t.start()

    def state():
        return load(t.root)[1]

    def assert_pass(index):
        result = state()["attempts"][-1]["steps"][index]
        assert result["status"] == "PASS", result

    def control(key):
        t.key("W")
        t.wait_screen(lambda s: "Next step" in s, "guide controls")
        t.key(key, settle=0.3)

    def jump(key):
        number = next(i + 1 for i, case in enumerate(CASES) if case["key"] == key)
        control("j")
        t.wait_screen(lambda s: "Case number" in s, "case chooser")
        t.key(str(number))
        enter(t)
        t.wait_screen(lambda s: f"{number}/{len(CASES)} " in s, "new case")
        root = Path(state()["attempts"][-1]["root"])
        t.wait(lambda s: s["cwd"] == str(root / "dest") and not s["running"])
        return root

    t.wait_screen(lambda s: "[W] Controls" in s and "CMM" in s, "initial guide and rows")
    control("n")
    assert state()["attempts"][0]["step"] == 0, "Unanswered observation advanced"
    control("p")
    t.wait_screen(lambda s: "Visual: PASS" in s, "recorded observation")
    control("n")
    t.wait_screen(lambda s: "step 2/2" in s, "next step")
    original = Path(v["root"])
    control("r")
    t.wait_screen(lambda s: "step 1/2" in s, "fresh restart")
    assert Path(state()["attempts"][-1]["root"]) != original and original.exists()
    control("h")
    assert "[W] Controls" not in t.capture(), "Hidden guide still rendered"
    control("h")
    t.wait_screen(lambda s: "[W] Controls" in s, "guide restored")
    t.tmux("resize-window", "-t", "test", "-x", "80", "-y", "18")
    t.wait_screen(lambda s: "W: controls" in s, "compact guide")
    t.tmux("resize-window", "-t", "test", "-x", "140", "-y", "40")
    t.wait_screen(lambda s: "[W] Controls" in s, "full guide after resize")
    jump("names")
    control("p"); control("n")
    t.wait_screen(lambda s: "step 2/2" in s, "last names step")
    control("s")
    t.wait_screen(lambda s: "Observation / skip reason" in s, "skip reason")
    enter(t)
    t.wait_screen(lambda s: "Visual: SKIP" in s, "recorded skip")
    control("d")
    t.wait_screen(lambda s: "Enter: next | b: back | q: return to Yazi" in s, "skipped step diagnostics")
    t.key("q"); enter(t)
    t.wait_screen(lambda s: "Visual: SKIP" in s, "skip retained after diagnostics")
    control("n")
    t.wait_screen(lambda s: "3/24 Manual refresh" in s, "next case after skipped step")
    assert state()["results"][1] == "SKIP", state()["results"]
    jump("git")
    control("n")
    t.wait_screen(lambda s: "Walk complete" in s, "completed walk")
    control("r")
    t.wait_screen(lambda s: "24/24 git.yazi coexistence" in s and "Walk complete" not in s, "reopened last case")
    assert not state()["finished"]
    control("n")
    t.wait_screen(lambda s: "Walk complete" in s, "completed restarted walk")
    root = jump("refresh")
    assert not state()["finished"]
    print("PASS guide: SKIP survives diagnostics/case change; restart and jump restore case titles after completion")
    control("p"); control("n")
    assert (root / "source/local").read_text() == "local edit\n"
    t.key("R")
    t.wait(lambda s: (s.get("records") or {}).get(str(root / "dest/local"), {}).get("xy") == "  ")
    control("p")
    assert_pass(1)
    control("n"); t.key("R")
    t.wait(lambda s: (s.get("records") or {}).get(str(root / "dest/local"), {}).get("xy") == "MM")
    print("PASS guide: display, verdict gate, fresh restart, hide, resize, preparation and real refresh")
    root = jump("visual-unset")
    t.key("1"); t.key(" "); t.key("j"); t.key(" "); t.key("j"); t.key(" ")
    t.key("1"); t.key("V"); t.key("j")
    control("h")  # Opening/closing controls must not escape visual mode.
    t.key("a")
    t.wait_screen(lambda s: "Press Enter to return to Yazi" in s, "visual unset Add")
    enter(t)
    t.wait(lambda s: not s["action_busy"])
    assert (root / "source/range-c").exists()
    assert not (root / "source/range-a").exists() and not (root / "source/range-b").exists()
    control("h")
    print("PASS guide controls preserve visual unset selection for real actions")
    root = jump("theme")
    control("p"); control("n"); t.key("Y")
    control("p")
    assert_pass(1)
    control("n"); t.key("Y"); control("p")
    assert_pass(2)
    root = jump("edit")
    t.key("6"); t.key("e")
    t.wait_screen(lambda s: "New source content" in s, "fixture editor")
    t.key("edited by fixture"); enter(t)
    finish(t)
    control("p")
    assert_pass(0)
    root = jump("encryption")
    t.key("7"); t.key("z"); finish(t); control("p")
    assert_pass(0)
    root = jump("template-add")
    t.key("7"); t.key("t"); finish(t); control("p")
    assert_pass(0)
    root = jump("edit-apply")
    t.key("6"); t.key("E")
    t.wait_screen(lambda s: "New source content" in s, "edit-and-apply editor")
    t.key("edited by fixture"); enter(t)
    finish(t, next_command=True); finish(t, next_confirm=True); confirm(t, False)
    control("p")
    assert_pass(0)
    root = jump("navigation")
    t.key("G"); t.key("H")
    root = jump("confirmation")
    # Changing cases must dispose of old tabs, and select every exact target.
    t.key("4", settle=0.8); t.key("x")
    t.wait_screen(lambda s: "Continue?" in s and "Targets: 6" in s, "long target selection")
    confirm(t, yes=False)
    assert all((root / "dest" / name).exists() for name in json.loads((root / "long.json").read_text()))
    print("PASS guide: theme epoch, terminal editor, encrypted Add, tab reset and exact long targets")
    root = jump("source-protection")
    t.key("5"); t.key("x")
    t.wait_screen(lambda s: "contains the source" in s, "source-ancestor rejection")
    control("d")
    t.wait_screen(lambda s: "Enter: next | b: back | q: return to Yazi" in s, "same-terminal details")
    t.key("q"); enter(t)
    t.wait_screen(lambda s: "[W] Controls" in s, "return from details")
    t.key("q")
    t.wait_screen(lambda s: "Save, retain fixtures and exit" in s, "finish menu")
    t.key("k")
    time.sleep(0.3)
    assert state()["exit"]["keep"] is True
    print("PASS guide: source protection, foreground details and saved exit choice")


def foreground_launcher():
    import sys
    before = set((REPO / ".dev/manual-runs").glob("*/results.json"))
    with fixture() as t:
        t.tmux("new-session", "-d", "-s", "test", "-x", "140", "-y", "40",
               sys.executable, str(REPO / "test/manual.py"))
        t.started = True
        t.tmux("set-option", "-w", "remain-on-exit", "on")
        t.wait_screen(lambda s: "[W] Controls" in s and "CMM" in s, "foreground launcher")
        t.key("q")
        t.wait_screen(lambda s: "Save and exit; clean fixtures" in s, "launcher finish menu")
        t.key("c")
        t.wait_screen(lambda s: "Results:" in s, "archived launcher report")
    reports = set((REPO / ".dev/manual-runs").glob("*/results.json")) - before
    assert len(reports) == 1, reports
    report = json.loads(next(iter(reports)).read_text())
    assert not Path(report["session"]).exists()
    assert all(not Path(a["root"]).exists() for a in report["attempts"])
    print("PASS foreground launcher: one process, in-Yazi exit, archive then ownership-checked cleanup")


def backend_paths():
    """Exercise real fixture setup and separate CLI processes, without git UI."""
    import shutil
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
                for attempt in load(t.root)[1]["attempts"]:
                    shutil.rmtree(owned(attempt["root"]))
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
                import shutil
                for attempt in load(t.root)[1]["attempts"]:
                    shutil.rmtree(owned(attempt["root"]))

    foreground_launcher()


if __name__ == "__main__":
    main()
