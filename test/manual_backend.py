"""Fixture preparation and durable progress behind the in-Yazi guide."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
from manual_cases import CASES
from support import REPO, Runtime, baseline, environment, owned, read, run, write


def save(root, state):
    temporary = root / "walk.json.tmp"
    write(temporary, json.dumps(state, indent=2, ensure_ascii=True))
    temporary.replace(root / "walk.json")


def load(root):
    root = owned(root)
    return root, json.loads(read(root / "walk.json"))


def context(path):
    root = owned(path)
    t = Runtime.__new__(Runtime)
    t.root, t.dest = root, root / "dest"
    t.source = Path(json.loads(read(root / "attempt.json"))["opts"]["source"])
    t.cfg, t.env = root / "config/chezmoi.toml", environment(root)
    from support import chezmoi_args
    t.args = chezmoi_args(root)
    t.args[t.args.index("--source") + 1] = str(t.source)
    return t


def prepare(t, operations, session):
    for operation in operations:
        name, *args = operation
        if name == "write":
            path = t.root / args[0]
            path.parent.mkdir(parents=True, exist_ok=True)
            write(path, args[1])
        elif name == "remove":
            (t.root / args[0]).unlink(missing_ok=True)
        elif name == "match":
            write(t.source / args[0], read(t.dest / args[0]))
        elif name == "editor":
            write(t.root / "editor-mode", args[0])
            editor_args = [str(REPO / "test/editor.py"), str(t.root)]
            write(t.cfg, '[edit]\ncommand=' + json.dumps(sys.executable) + '\nargs=' + json.dumps(editor_args) + '\napply=true\nwatch=true\n')
        elif name == "age":
            identity = t.root / "age-identity"
            write(identity, "AGE-SECRET-KEY-1KTYK6RVLN5TAPE7VF6FQQSKZ9HWWCDSKUGXXNUQDWZ7XXT5YK5LSF3UTKQ\n")
            identity.chmod(0o600)
            write(t.cfg, 'encryption="age"\nuseBuiltinAge=true\n[age]\nidentity=' + json.dumps(str(identity)) + '\nrecipient="age1gde3ncmahlqd9gg50tanl99r960llztrhfapnmx853s4tjum03uqfssgdh"\n')
        elif name == "ranges":
            for prefix in ["range", "menu"]:
                for char in "abc":
                    write(t.dest / f"{prefix}-{char}", f"range {char}\n" if prefix == "range" else f"menu {char}\n")
            write(t.dest / ".config/outside", "outside\n")
        elif name == "nested-source":
            t.source = t.dest / ".local/share/chezmoi"
            (t.source / "dot_local/bin").mkdir(parents=True)
            write(t.source / "dot_local/bin/tool", "tool\n")
            write(t.source / "dot_bashrc", "unrelated\n")
            (t.dest / ".local/bin").mkdir(parents=True)
            write(t.dest / ".local/bin/tool", "tool\n")
        elif name == "long":
            names = [str(i) + "a" * 170 + "日本語" * 5 + "\\\n-end-" + str(i) for i in range(5)]
            names.append("/".join(["deep"] + ["d" * 90] * 7 + ["last-target"]))
            for target in names:
                for directory in [t.source, t.dest]:
                    path = directory / target
                    path.parent.mkdir(parents=True, exist_ok=True)
                    write(path, "confirmation fixture\n")
            write(t.root / "long.json", json.dumps(names))
        elif name == "theme":
            config = session / "config"
            if args[0] == "base":
                write(config / "theme.toml", read(session / "baseline-theme.toml"))
            else:
                flavor = config / "flavors/manual.yazi"
                flavor.mkdir(parents=True, exist_ok=True)
                write(flavor / "tmtheme.xml", '<?xml version="1.0"?><plist version="1.0"><dict><key>name</key><string>manual</string><key>settings</key><array/></dict></plist>\n')
                write(flavor / "flavor.toml", '[chezmoi]\nmanaged_sign="F"\nmodified_sign="m"\nmodified={fg="#ff8800"}\n')
                write(config / "theme.toml", read(session / "baseline-theme.toml") + '[flavor]\ndark="manual"\nlight="manual"\n[chezmoi]\nmanaged_sign="界"\n')
        else:
            raise ValueError(f"Unknown fixture operation: {name}")


def current(state):
    return state["attempts"][state["active"]]


def view(state):
    attempt = current(state)
    spec = CASES[attempt["case"]]
    instruction = spec["steps"][attempt["step"]]
    unavailable = spec["optional"] == "git" and not state["git_plugin"]
    return dict(title=spec["title"], case=attempt["case"] + 1, total=len(CASES),
                step=attempt["step"] + 1, steps=len(spec["steps"]), instruction="SKIP: no --git-plugin supplied. W/n continues." if unavailable else instruction["do"],
                expect=instruction["expect"], result=attempt["steps"][attempt["step"]],
                root=attempt["root"], opts=attempt["opts"], token=f'{state["active"]}:{attempt["step"]}',
                cases=[dict(title=c["title"], optional=c["optional"], result=state["results"][i]) for i, c in enumerate(CASES)],
                targets=json.loads(read(Path(attempt["root"]) / "long.json")) if spec["key"] == "confirmation" else [],
                finished=state.get("finished", False))


def start_case(root, state, index):
    if index < 0 or index >= len(CASES):
        raise ValueError("Invalid case index")
    spec = CASES[index]
    write(root / "config/theme.toml", read(root / "baseline-theme.toml"))
    t = Runtime(state["git_plugin"], probe=False)
    try:
        write(t.root / "manual.json", json.dumps(dict(version=1, root=str(t.root), repo=str(REPO))))
        baseline(t)
        prepare(t, spec["setup"], root)
        opts = dict(command=str(t.root / "chezmoi-wrapper"), config=str(t.cfg), source=str(t.source),
                    destination=str(t.dest), persistent_state=str(t.root / "chezmoi.db"), cache=str(t.root / "cache/chezmoi"),
                    timeout=1, cache_ttl=0.2, error_backoff=0.5)
        write(t.root / "attempt.json", json.dumps(dict(opts=opts)))
        attempt = dict(case=index, root=str(t.root), opts=opts, step=0,
                       steps=[dict(visual="unanswered", status="NOT RUN") for _ in spec["steps"]])
        state["attempts"].append(attempt)
        state["active"] = len(state["attempts"]) - 1
        state["results"][index] = "NOT RUN"
        if spec["optional"] == "git" and not state["git_plugin"]:
            for result in attempt["steps"]:
                result.update(status="SKIP", visual="SKIP", note="No --git-plugin supplied")
        prepare_step(root, state)
    except BaseException:
        if state["attempts"] and state["attempts"][-1]["root"] == str(t.root):
            state["attempts"].pop()
            state["active"] = max(0, len(state["attempts"]) - 1)
        t.close()
        raise


def prepare_step(root, state):
    attempt = current(state)
    t = context(attempt["root"])
    spec = CASES[attempt["case"]]["steps"][attempt["step"]]
    prepare(t, spec["prep"], root)
    calls = t.root / "state/instrument/calls"
    attempt["call_offset"] = calls.stat().st_size if calls.exists() else 0
    attempt["epoch_before"] = None


def initialize(root, git_plugin):
    versions = {name: run([name, "--version"]).strip() for name in ["yazi", "chezmoi"]}
    diff = run(["git", "diff", "HEAD"], cwd=REPO)
    state = dict(version=1, session=str(root), git_plugin=git_plugin, versions=versions,
                 head=run(["git", "rev-parse", "HEAD"], cwd=REPO).strip(), diff_sha256=hashlib.sha256(diff.encode()).hexdigest(),
                 source_hashes={str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for pattern in ["*.lua", "test/*.lua", "test/*.py"] for p in REPO.glob(pattern)},
                 results=["NOT RUN"] * len(CASES), attempts=[], finished=False)
    start_case(root, state, 0)
    save(root, state)
    return view(state)


def check(state, snapshot):
    attempt = current(state)
    spec = CASES[attempt["case"]]["steps"][attempt["step"]]
    root = owned(attempt["root"])
    failures = []
    for relative, expected in spec["files"].items():
        path = root / relative
        if not path.is_file() or read(path) != expected:
            failures.append(f"{relative}: expected {expected!r}")
    for relative in spec["absent"]:
        if (root / relative).exists() or (root / relative).is_symlink():
            failures.append(f"{relative}: expected absent")
    calls = root / "state/instrument/calls"
    if spec["no_action"]:
        offset = attempt["call_offset"] if spec["special"] == "no-new-destroy" else 0
        for line in (calls.read_bytes()[offset:].decode() if calls.exists() else "").splitlines():
            args = json.loads(line)
            if "--no-tty" not in args and spec["no_action"] in args:
                failures.append(f'Interactive {spec["no_action"]} must not be invoked')
    diagnostic = []
    for name, expected in spec["records"].items():
        actual = (snapshot.get("records") or {}).get(str(root / "dest" / name), {})
        for key, value in expected.items():
            # Missing false flags and explicit false flags are equivalent.
            if actual.get(key, False if value is False else None) != value:
                diagnostic.append(f"{name}.{key}: expected {value!r}, got {actual.get(key)!r}")
    special = spec["special"]
    if special == "template-added" and not (root / "source/unmanaged.tmpl").is_file():
        failures.append("source/unmanaged.tmpl: expected template")
    if special == "encrypted-added":
        encrypted = root / "source/encrypted_unmanaged.age"
        if not encrypted.is_file():
            failures.append("Expected disposable age-encrypted source entry")
        else:
            data = encrypted.read_bytes()
            if not data.startswith((b"age-encryption.org/v1", b"-----BEGIN AGE ENCRYPTED FILE-----")):
                failures.append("Expected age header (binary or armored)")
            if context(root).chezmoi("decrypt", encrypted) != "other\n":
                failures.append("Encrypted entry must decrypt to original fixture contents")
    if special == "long-preserved":
        for name in json.loads(read(root / "long.json")):
            for directory in ["source", "dest"]:
                path = root / directory / name
                if not path.exists() or read(path) != "confirmation fixture\n":
                    failures.append(f"Long target changed: {directory}/{name!r}")
    if special in {"theme-custom", "theme-base"}:
        signs = snapshot.get("signs") or {}
        expected = "界" if special == "theme-custom" else "C"
        if special == "theme-custom" and signs.get("modified") != "m":
            diagnostic.append("Expected flavor modified sign m")
        if signs.get("managed") != expected:
            diagnostic.append(f"Expected managed sign {expected!r}, got {signs}")
        if attempt["epoch_before"] is not None and snapshot.get("epoch") != attempt["epoch_before"]:
            diagnostic.append("Theme reload advanced status epoch")
    write(root / "snapshot.json", json.dumps(snapshot, indent=2))
    return dict(files="FAIL" if failures else "PASS", failures=failures,
                diagnostic="FAIL" if diagnostic else "PASS", diagnostic_failures=diagnostic)


def transition(root, operation, payload):
    root, state = load(root)
    attempt = current(state)
    token = f'{state["active"]}:{attempt["step"]}'
    if payload.get("token") != token:
        raise ValueError("Stale guide request; reopen controls")
    snapshot = payload.get("snapshot", {})
    result = attempt["steps"][attempt["step"]]
    result.pop("message", None)
    if CASES[attempt["case"]]["optional"] == "git" and not state["git_plugin"] and operation in {"check", "pass", "fail"}:
        save(root, state)
        return view(state)
    if operation in {"check", "pass", "fail"}:
        result.pop("error", None)
        result.update(check(state, snapshot))
        if operation != "check":
            result["visual"] = "PASS" if operation == "pass" else "FAIL"
            result["note"] = payload.get("note", "")
        result["status"] = ("FAIL" if "FAIL" in [result["files"], result["diagnostic"], result["visual"]]
                            else "PASS" if result["visual"] == "PASS" else "NOT RUN")
    elif operation == "baseline":
        attempt["epoch_before"] = snapshot.get("epoch")
    elif operation == "skip":
        result.update(status="SKIP", visual="SKIP", note=payload.get("note") or "Skipped by tester")
    elif operation == "next":
        if result["visual"] not in {"PASS", "FAIL", "SKIP"}:
            result.update(check(state, snapshot))
            result["message"] = "Record visual PASS/FAIL or SKIP before advancing."
        elif attempt["step"] + 1 < len(attempt["steps"]):
            attempt["step"] += 1
            prepare_step(root, state)
        else:
            statuses = [s["status"] for s in attempt["steps"]]
            state["results"][attempt["case"]] = "FAIL" if "FAIL" in statuses else "SKIP" if "SKIP" in statuses else "PASS"
            index = attempt["case"] + 1
            while index < len(CASES) and CASES[index]["optional"] == "git" and not state["git_plugin"]:
                state["results"][index] = "SKIP"
                state.setdefault("skip_reasons", {})[str(index)] = "No --git-plugin supplied"
                index += 1
            if index < len(CASES):
                start_case(root, state, index)
            else:
                state["finished"] = True
    elif operation in {"restart", "jump"}:
        start_case(root, state, attempt["case"] if operation == "restart" else int(payload["index"]))
    elif operation == "finish":
        state["exit"] = dict(keep=payload.get("keep", True))
    else:
        raise ValueError(f"Unknown guide operation: {operation}")
    attempt = current(state)
    if any("FAIL" in [s.get("files"), s.get("diagnostic"), s.get("visual")] or s["status"] == "ERROR" for s in attempt["steps"]):
        attempt["failed"] = True
    statuses = [s["status"] for s in attempt["steps"]]
    state["results"][attempt["case"]] = ("ERROR" if "ERROR" in statuses else "FAIL" if "FAIL" in statuses
                                           else "NOT RUN" if "NOT RUN" in statuses else "SKIP" if "SKIP" in statuses else "PASS")
    save(root, state)
    return view(state)


def details(root):
    root, state = load(root)
    attempt = current(state)
    fixture = owned(attempt["root"])
    spec = CASES[attempt["case"]]
    lines = [f'{spec["title"]} - step {attempt["step"] + 1}/{len(spec["steps"])}', "",
             "DO: " + spec["steps"][attempt["step"]]["do"], "", "EXPECT: " + spec["steps"][attempt["step"]]["expect"], "",
             "Signs are MXYD (plus leading separator). C=managed; XY=chezmoi status; *=directory change; !=failure.",
             "Spaces are significant: clean='C   ', local='CMM ', source='C M ', unmanaged='    '.", "",
             "CURRENT RESULT", json.dumps(attempt["steps"][attempt["step"]], indent=2), "",
             "CASES"]
    lines += [f'{i + 1:2}. {c["title"]}: {state["results"][i]}' for i, c in enumerate(CASES)]
    lines += ["", "VERSIONS", json.dumps(state["versions"], indent=2), "", f"Fixture: {fixture}"]
    for relative in ["snapshot.json", "state/instrument/calls", "editor-targets.json"]:
        path = fixture / relative
        if path.is_file():
            lines += ["", relative, read(path)[-24000:]]
    lines += ["", "SOURCE / DEST CONTENTS (JSON escaped; at most 80 files per tree)"]
    for directory in [Path(attempt["opts"]["source"]), fixture / "dest"]:
        for path in sorted(directory.rglob("*"))[:80]:
            if path.is_file() and not path.is_symlink() and path.stat().st_size <= 4096:
                lines.append(json.dumps({str(path.relative_to(fixture)): read(path)}, ensure_ascii=True))
    for path in (root / "state").rglob("*.log"):
        lines += ["", str(path.relative_to(root)), read(path)[-12000:]]
    text = "\n".join(lines).splitlines()
    import textwrap
    width = max(20, shutil.get_terminal_size().columns - 2)
    text = [piece for line in text for piece in (textwrap.wrap(line, width, replace_whitespace=False) or [""])]
    page, height = 0, max(4, shutil.get_terminal_size().lines - 3)
    while True:
        print("\033[2J\033[H" + "\n".join(text[page:page + height]), flush=True)
        answer = input("Enter: next | b: back | q: return to Yazi > ").strip().lower()
        if answer == "q" or (not answer and page + height >= len(text)):
            return
        page = max(0, page - height) if answer == "b" else min(len(text) - 1, page + height)


def finalize(root):
    root, state = load(root)
    if (root / "manual-error.json").exists():
        state["harness_error"] = json.loads(read(root / "manual-error.json"))
        state["results"][current(state)["case"]] = "ERROR"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    archive = REPO / ".dev/manual-runs" / stamp
    archive.mkdir(parents=True)
    write(archive / "results.json", json.dumps(state, indent=2))
    for i, attempt in enumerate(state["attempts"]):
        fixture = owned(attempt["root"])
        directory = archive / f"attempt-{i + 1}"
        directory.mkdir()
        for relative in ["snapshot.json", "initial.diff", "state/instrument/calls", "editor-targets.json", "attempt.json"]:
            path = fixture / relative
            if path.is_file():
                target = directory / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
    shutil.copytree(root / "state", archive / "session-state")
    if (root / "manual-error.json").exists():
        shutil.copyfile(root / "manual-error.json", archive / "manual-error.json")
    failed = (root / "manual-error.json").exists() or any(a.get("failed") or s["status"] in {"FAIL", "ERROR"} or s.get("files") == "FAIL" or s.get("diagnostic") == "FAIL" for a in state["attempts"] for s in a["steps"])
    keep = state.get("exit", {}).get("keep", True) or failed
    print(f"Results: {archive / 'results.json'}")
    if keep:
        print(f"Fixtures retained: {root}")
    else:
        for attempt in state["attempts"]:
            shutil.rmtree(owned(attempt["root"]))
        shutil.rmtree(root)
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("operation")
    parser.add_argument("payload", nargs="?", default="{}")
    args = parser.parse_args()
    if args.operation == "details":
        details(Path(args.root))
    else:
        root = owned(args.root)
        try:
            value = transition(root, args.operation, json.loads(args.payload))
        except Exception as error:
            _, state = load(root)
            current(state)["steps"][current(state)["step"]].update(status="ERROR", error=str(error))
            current(state)["failed"] = True
            save(root, state)
            value = view(state)
        print(json.dumps(value))


if __name__ == "__main__":
    main()
