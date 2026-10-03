"""Terminal-driven command acceptance shared by runtime and black-box E2E."""
import json
import re
import shlex
import time
import sys
import screen
from support import REPO, NAMES, lua, read, write


def configure(t):
    keys = {
        "a": "plugin chezmoi -- add", "r": "plugin chezmoi -- re-add",
        "e": "plugin chezmoi -- edit", "p": "plugin chezmoi -- apply",
        "d": "plugin chezmoi -- diff", "f": "plugin chezmoi -- forget",
        "x": "plugin chezmoi -- destroy", "D": "plugin chezmoi -- destroy --recursive=false",
        "v": "plugin chezmoi -- edit --apply",
        "t": "plugin chezmoi -- add --template", "z": "plugin chezmoi -- add --encrypt",
        "u": "plugin chezmoi -- add --recursive=false",
        "s": "toggle", "S": "escape --select",
    }
    for key, name in {"1": "clean", "2": "unmanaged", "3": "source", "4": ".config",
                      "5": "local", "6": "space name"}.items():
        keys[key] = "reveal " + shlex.quote(str(t.dest / name))
    cfg = t.root / "config/keymap.toml"
    write(cfg, read(cfg) + ''.join(
        f'[[mgr.prepend_keymap]]\non={json.dumps(k)}\nrun={json.dumps(v)}\n' for k, v in keys.items()))


def enter(t):
    t.tmux("send-keys", "-t", "test", "Enter")


def returned(t):
    t.wait_screen(lambda s: "Press Enter to return to Yazi" not in s and "Continue?" not in s,
                  "Yazi restored")
    time.sleep(0.15)


def finish(t, next_confirm=False, success=True, next_command=False):
    screen = t.wait_screen(lambda s: "Press Enter to return to Yazi" in s, "command exit prompt")
    assert ("chezmoi exited with code 0." in screen) == success, screen
    enter(t)
    if next_confirm:
        t.wait_screen(lambda s: "Continue?" in s, "confirmation after command")
    elif not next_command:
        returned(t)
    return screen


def confirm(t, yes=True):
    while True:
        capture = t.wait_screen(lambda s: "Continue?" in s, "plugin confirmation")
        match = re.search(r"chezmoi \S+ \((\d+)/(\d+)\)", capture)
        assert match, capture
        page, total = map(int, match.groups())
        t.key("y" if yes else "n")
        if not yes or page == total:
            return
        t.wait_screen(lambda s: f"({page + 1}/{total})" in s, "next confirmation page")


def native_confirm(t):
    t.wait_screen(lambda s: "yes/no/all/quit" in s,
                  "chezmoi native confirmation")
    t.key("y")


def commands(t):
    configure(t)
    t.start()
    t.key("2")
    t.key("a")
    finish(t)
    assert read(t.source / "unmanaged") == read(t.dest / "unmanaged")
    t.wait_screen(lambda s: screen.status(s, "unmanaged") == "C   ", "managed status after add")
    write(t.dest / "unmanaged", "changed by destination\n")
    t.key("r")
    finish(t)
    assert read(t.source / "unmanaged") == "changed by destination\n"
    # Menu dispatch follows exactly the same path as a direct binding.
    write(t.dest / "unmanaged", "menu change\n")
    t.key("C")
    t.wait_screen(lambda s: "Re-add" in s, "action menu")
    t.key("r")
    finish(t)
    assert read(t.source / "unmanaged") == "menu change\n"
    t.key("f")
    confirm(t)
    native_confirm(t)
    finish(t)
    assert not (t.source / "unmanaged").exists() and (t.dest / "unmanaged").exists()
    t.wait_screen(lambda s: screen.status(s, "unmanaged") == "    ", "unmanaged status after forget")
    t.key("a")
    finish(t)
    t.key("x")
    confirm(t)
    native_confirm(t)
    finish(t)
    assert not (t.source / "unmanaged").exists() and not (t.dest / "unmanaged").exists()
    t.wait_screen(lambda s: screen.row(s, "unmanaged") is None, "row removed after destroy")
    # Apply requires a successful diff and an explicit plugin confirmation.
    t.key("3")
    t.key("p")
    finish(t, next_confirm=True)
    confirm(t, False)
    assert read(t.dest / "source") == "original\n"
    t.key("p")
    finish(t, next_confirm=True)
    confirm(t)
    finish(t)
    assert read(t.dest / "source") == "source edit\n"
    t.wait_screen(lambda s: screen.status(s, "source") == "C   ",
                  "status after apply")
    t.key("5"); t.key("p"); finish(t, next_confirm=True); confirm(t)
    t.wait_screen(lambda s: "overwrite" in s and "skip" in s, "native apply conflict")
    t.key("q"); finish(t)
    assert read(t.dest / "local") == "local edit\n"
    (t.source / "source").rename(t.source / "source.tmpl")
    write(t.source / "source.tmpl", "{{ .missing.field }}")
    t.key("3"); t.key("p"); finish(t, success=False)
    assert read(t.dest / "source") == "source edit\n"
    assert "runtime error:" not in t.logs(), t.logs()
    print("PASS terminal actions: add, re-add, menu, forget, destroy, apply/cancel/conflict, failed diff")


def bind_targets(t, names):
    cfg = t.root / "config/keymap.toml"
    content, bindings = read(cfg), {}
    for i, name in enumerate(names):
        key = chr(ord('a') + i)
        bindings[name] = "g" + key
        content += ('[[mgr.prepend_keymap]]\n' + 'on=' + json.dumps(["g", key]) + '\nrun='
                    + json.dumps("reveal " + shlex.quote(str(t.dest / name))) + '\n')
    write(cfg, content)
    return bindings


def source_ancestor(t):
    configure(t)
    nested = t.dest / ".local/share/chezmoi"
    nested.parent.mkdir(parents=True)
    init = t.root / "config/init.lua"
    write(init, read(init).replace(lua(t.source), lua(nested)))
    t.source.rename(nested)
    t.args[t.args.index("--source") + 1] = str(nested)
    t.source = nested
    (t.source / "dot_local/bin").mkdir(parents=True)
    write(t.source / "dot_local/bin/tool", "managed tool\n")
    write(t.source / "dot_bashrc", "unrelated source entry\n")
    targets = [t.dest / ".local/bin", t.dest / ".bashrc"]
    write(t.root / "nested-source.diff", t.chezmoi("diff", *targets))
    t.chezmoi("apply", *targets)
    keys = bind_targets(t, [".local", ".local/share"])
    t.start()
    for name, action, mixed in [(".local", "x", False), (".local/share", "x", False),
                                (".local", "x", True), (".local", "D", False)]:
        t.wait_screen(lambda s: "contains the source directory" not in s,
                      "previous rejection cleared")
        t.key("S")
        if mixed:
            t.key("1"); t.key("s")
        t.key(keys[name])
        if mixed:
            t.key("s")
        before = read(t.calls) if t.calls.exists() else None
        t.key(action)
        capture = t.wait_screen(lambda s: "contains the source directory" in s,
                                "source ancestor rejected before confirmation")
        assert "Continue?" not in capture and "yes/no/all/quit" not in capture
        if before is not None:
            calls = [json.loads(line) for line in read(t.calls)[len(before):].splitlines()]
            assert not any("destroy" in args and "--no-tty" not in args for args in calls)
        assert read(t.source / "dot_bashrc") == read(t.dest / ".bashrc") == "unrelated source entry\n"
        assert read(t.source / "dot_local/bin/tool") == read(t.dest / ".local/bin/tool") == "managed tool\n"
        assert read(t.source / "clean") == read(t.dest / "clean") == "original\n"
    assert "runtime error:" not in t.logs(), t.logs()
    print("PASS source ancestor rejection: recursive, nonrecursive, unmanaged parent, mixed selection")


def visual_selection(t):
    configure(t)
    cfg = t.root / "config/keymap.toml"
    # The action suite uses v for edit-and-apply; restore visual mode here.
    write(cfg, read(cfg).replace('run="plugin chezmoi -- edit --apply"', 'run="visual_mode"'))
    names = ["visual/" + name for name in ["a", "b", "c", "d", "e", "f"]]
    (t.dest / "visual").mkdir()
    for name in names:
        write(t.dest / name, "visual selection\n")
    keys = bind_targets(t, names)
    t.start()
    t.key(keys[names[0]]); t.key("v"); t.key("j"); t.key("j"); t.key("a")
    capture = t.wait_screen(lambda s: "Continue?" in s, "visual range confirmation")
    assert "Targets: 3" in capture, capture
    confirm(t, False)
    returned(t)
    assert not any((t.source / name).exists() for name in names)
    t.key("a"); confirm(t); finish(t)
    assert all(read(t.source / name) == "visual selection\n" for name in names[:3])
    assert not any((t.source / name).exists() for name in names[3:])
    t.key("S")
    # Preserve a selection outside the current directory when committing a range.
    t.key("1"); t.key("s")
    t.key(keys[names[3]]); t.key("v"); t.key("j"); t.key("j"); t.key("C")
    t.wait_screen(lambda s: "Add options" in s, "visual range menu snapshot")
    t.key("a")
    capture = t.wait_screen(lambda s: "Continue?" in s, "menu visual range confirmation")
    assert "Targets: 4" in capture, capture
    confirm(t); finish(t)
    assert all(read(t.source / name) == "visual selection\n" for name in names)
    t.key("S")
    # Unset mode must remove the range from the existing selection.
    for name in names[:3]:
        t.key(keys[name]); t.key("s")
    t.key(keys[names[0]]); t.key("V"); t.key("j"); t.key("f")
    capture = t.wait_screen(lambda s: "Continue?" in s, "visual unset confirmation")
    assert "Targets: 1" in capture and "/" + names[2] in capture, capture
    confirm(t, False)
    returned(t)
    assert all((t.source / name).exists() and (t.dest / name).exists() for name in names)
    assert "runtime error:" not in t.logs(), t.logs()
    print("PASS visual selection: direct add, cancellation, menu, cross-directory selection, unset")


def extended(t):
    configure(t)
    special = NAMES[4:] + ["$(touch sentinel)"]
    for name in special:
        write(t.dest / name, "literal path\n")
    folder = t.dest / "newdir"
    folder.mkdir()
    write(folder / "child", "child\n")
    (t.dest / "outside-link").symlink_to(t.root / "unmanaged-outside")
    replaced_dirs = ["directory-as-file", "directory-as-link"]
    for name in replaced_dirs:
        (t.source / name).mkdir()
        write(t.source / name / "child", "preserve source child\n")
    write(t.dest / replaced_dirs[0], "replacement file\n")
    (t.dest / replaced_dirs[1]).symlink_to("clean")
    keys = bind_targets(t, special + ["newdir", "outside-link"] + replaced_dirs)
    identity = t.root / "age-identity"
    write(identity, "AGE-SECRET-KEY-1KTYK6RVLN5TAPE7VF6FQQSKZ9HWWCDSKUGXXNUQDWZ7XXT5YK5LSF3UTKQ\n")
    identity.chmod(0o600)
    cfg = ('encryption="age"\nuseBuiltinAge=true\n[age]\nidentity=' + json.dumps(str(identity))
           + '\nrecipient="age1gde3ncmahlqd9gg50tanl99r960llztrhfapnmx853s4tjum03uqfssgdh"\n'
           + '[edit]\napply=true\nwatch=true\ncommand=' + json.dumps(sys.executable) + '\nargs='
           + json.dumps([str(REPO / "test/editor.py"), str(t.root)]) + '\n'
           + '[diff]\nexclude=["scripts"]\n')
    write(t.cfg, cfg)
    write(t.root / "editor-mode", "edit")
    t.start()
    # Multiple selection, literal path transport, and confirmation pagination.
    for name in special:
        t.key(keys[name]); t.key("s")
    t.key("a")
    confirm(t)
    finish(t)
    for name in special:
        assert read(t.source / name) == "literal path\n", name
    assert not (t.root / "sentinel").exists()
    t.key("S")
    # Mixed applicability stops all edits before opening the editor.
    t.key("1"); t.key("s"); t.key("2"); t.key("s"); t.key("e")
    t.wait_screen(lambda s: "Not managed by chezmoi" in s, "mixed selection rejection")
    assert not (t.root / "editor-targets.json").exists()
    t.key("S")
    t.key("4"); t.key("e")
    t.wait_screen(lambda s: "Select files inside" in s, "directory edit rejection")
    # Nonrecursive and recursive directory add have different scopes.
    t.key(keys["newdir"]); t.key("u"); confirm(t); finish(t)
    assert (t.source / "newdir").is_dir() and not (t.source / "newdir/child").exists()
    t.key("a"); confirm(t); finish(t)
    assert read(t.source / "newdir/child") == "child\n"
    # Chezmoi removes a directory's descendants even with --recursive=false.
    logged = t.calls.exists()
    before = read(t.calls) if logged else ""
    t.key("D")
    t.wait_screen(lambda s: "Non-recursive destroy" in s, "unsafe directory destroy rejected")
    if logged:
        new_calls = [json.loads(line) for line in read(t.calls)[len(before):].splitlines()]
        assert not any("destroy" in args and "--no-tty" not in args for args in new_calls), (
            "Unsafe directory destroy reached chezmoi")
    assert read(t.source / "newdir/child") == "child\n"
    assert read(t.dest / "newdir/child") == "child\n"
    # Source directories remain unsafe when the destination is a file or link.
    for name in replaced_dirs:
        before = read(t.calls) if logged else ""
        t.key("1"); t.key("s")
        t.key(keys[name]); t.key("s"); t.key("D")
        capture = t.wait_screen(lambda s: "Non-recursive destroy" in s and name in s,
                                "source directory rejects the entire selection")
        assert "Continue?" not in capture
        if logged:
            new_calls = [json.loads(line) for line in read(t.calls)[len(before):].splitlines()]
            assert not any("destroy" in args and "--no-tty" not in args for args in new_calls)
        assert read(t.source / name / "child") == "preserve source child\n"
        assert read(t.source / "clean") == read(t.dest / "clean") == "original\n"
        t.key("S")
    assert read(t.dest / replaced_dirs[0]) == "replacement file\n"
    assert (t.dest / replaced_dirs[1]).is_symlink()
    # A symlink is added as a symlink, never followed into its outside referent.
    t.key(keys["outside-link"]); t.key("a"); finish(t)
    assert (t.source / "symlink_outside-link").exists()
    assert not (t.root / "unmanaged-outside").exists()
    # A template is not overwritten by re-add.
    t.key("1"); t.key("t"); finish(t)
    original = read(t.source / "clean.tmpl")
    write(t.dest / "clean", "local template change\n")
    t.key("r"); finish(t)
    assert read(t.source / "clean.tmpl") == original
    # Encrypted add and transparent edit/re-encryption use chezmoi's editor.
    t.key("2"); t.key("z"); finish(t)
    assert (t.source / "encrypted_unmanaged.age").exists()
    t.key("e"); finish(t)
    assert t.chezmoi("cat", t.dest / "unmanaged") == "edited by fixture\n"
    assert read(t.dest / "unmanaged") == "other\n"
    # Edit-and-apply cancellation retains the source edit.
    t.key("3"); t.key("v")
    t.wait_screen(lambda s: "Press Enter to return to Yazi" in s, "edit exit before diff")
    assert read(t.dest / "source") == "original\n", "Native edit applied before preview"
    finish(t, next_command=True)
    finish(t, next_confirm=True)
    confirm(t, False)
    assert read(t.source / "source") == "edited by fixture\n"
    assert read(t.dest / "source") == "original\n"
    t.key("v")
    finish(t, next_command=True); finish(t, next_confirm=True); confirm(t); finish(t)
    assert read(t.dest / "source") == "edited by fixture\n"
    # Standalone diff follows diff.exclude; apply preview follows apply's scope.
    t.key("4"); t.key("d")
    screen = finish(t)
    assert "pending.sh" not in screen, screen
    t.key("p")
    screen = finish(t, next_confirm=True)
    assert "pending.sh" in screen, screen
    assert not (t.root / "script-ran").exists()
    confirm(t); finish(t)
    assert (t.root / "script-ran").exists()
    assert (t.dest / ".config/new").exists()
    # An editor waiting for input has a real TTY; Ctrl-C restores the UI.
    write(t.root / "editor-mode", "wait")
    t.key("6"); t.key("e")
    t.wait_screen(lambda s: "Fixture editor input:" in s, "interactive editor")
    t.key("typed via tty"); enter(t); finish(t)
    assert read(t.source / "space name") == "typed via tty\n"
    t.key("v")
    t.wait_screen(lambda s: "Fixture editor input:" in s, "interruptible editor")
    t.tmux("send-keys", "-t", "test", "C-c")
    finish(t, success=False)
    assert read(t.dest / "space name") == "literal path\n"
    # Partial editor failure keeps source changes and never advances to apply.
    write(t.root / "editor-mode", "partial-fail")
    t.key("v"); finish(t, success=False)
    assert read(t.source / "space name") == "edited by fixture\n"
    assert read(t.dest / "space name") == "literal path\n"
    t.key("R")
    assert "runtime error:" not in t.logs(), t.logs()
    print("PASS action edges: selections, literal paths, directories, links, encryption, editor, scripts, interruption")


def confirmation_pages(t):
    configure(t)
    names = [str(i) + "a" * 170 + "日本語" * 5 + "\\\n-end-" + str(i) for i in range(5)]
    names += ["/".join(["deep"] + ["d" * 90] * 7 + ["last-target"])]
    for name in names:
        for root in [t.dest, t.source]:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            write(path, "confirmation fixture\n")
    keys = bind_targets(t, names)
    t.start()
    for name in names:
        t.key(keys[name]); t.key("s")

    def body(capture):
        lines = capture.splitlines()
        top = next(i for i, line in enumerate(lines) if "╭" in line and "chezmoi destroy" in line)
        left = screen.cell_width(lines[top].split("╭")[0])
        width = screen.cell_width(lines[top].split("╭")[1].split("╮")[0])
        result = []
        for line in lines[top + 1:]:
            if "╰" in line:
                break
            column, text = 0, ""
            for char in line:
                if left < column <= left + width:
                    text += char
                column += screen.cell_width(char)
            if "[Y]es" not in text and "Continue?" not in text:
                result.append(text.strip())
        return "".join(result)

    for cols, rows in [(140, 40), (80, 18)]:
        t.tmux("resize-window", "-t", "test", "-x", cols, "-y", rows)
        time.sleep(0.2)
        t.key("x")
        reviewed, page = "", 1
        while True:
            capture = t.wait_screen(lambda s: f"chezmoi destroy ({page}/" in s and "Continue?" in s,
                                    "complete confirmation page")
            reviewed += body(capture)
            total = int(re.search(r"chezmoi destroy \(\d+/(\d+)\)", capture)[1])
            if page == total:
                t.key("n")
                break
            t.key("y")
            page += 1
        assert total > 1
        for name in names:
            escaped = str(t.dest / name).replace("\\", "\\\\").replace("\n", "\\x0a")
            assert escaped in reviewed, (escaped, reviewed)
            assert (t.source / name).exists() and (t.dest / name).exists(), "Cancellation mutated a target"

    # Accepting a page after a resize must restart review, never skip clipped text.
    t.tmux("resize-window", "-t", "test", "-x", 140, "-y", 40)
    time.sleep(0.2)
    t.key("x")
    t.wait_screen(lambda s: "chezmoi destroy (1/" in s, "initial review page")
    t.tmux("resize-window", "-t", "test", "-x", 80, "-y", 18)
    time.sleep(0.2)
    t.key("y")
    t.wait_screen(lambda s: "chezmoi destroy (1/" in s and "Continue?" in s and "Pane resized" in s,
                  "review restarts after resize")
    t.key("n")
    assert all((t.source / name).exists() and (t.dest / name).exists() for name in names)
    t.tmux("resize-window", "-t", "test", "-x", 40, "-y", 12)
    time.sleep(0.2)
    t.key("x")
    t.wait_screen(lambda s: "Enlarge the current pane" in s, "too-small pane rejected")
    assert all((t.source / name).exists() and (t.dest / name).exists() for name in names)
    assert "runtime error:" not in t.logs(), t.logs()
    print("PASS confirmation pages: complete long/Unicode/control paths, small pane, cancellation, resize")
