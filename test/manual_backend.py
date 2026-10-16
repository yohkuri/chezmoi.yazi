"""Fixture preparation and durable progress behind the in-Yazi guide."""
import argparse
from datetime import datetime, timezone
import hashlib
import heapq
import json
from pathlib import Path
import shutil
import sys
from manual_cases import CASES
from support import REPO, Runtime, baseline, environment, owned, read, run, write


class StaleRequest(ValueError):
    """A delayed guide request must not change the current observation."""


class PreparationError(RuntimeError):
    """Fixture preparation failed before the target step became active."""

    def __init__(self, case, step, error):
        super().__init__(str(error))
        self.case, self.step = case, step


def save(root, state):
    update_results(state)
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
                    write(t.dest / f"{prefix}-{char}", f"{prefix} {char}\n")
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


def case_status(attempt):
    statuses = {step["status"] for step in attempt["steps"]}
    return next((status for status in ["ERROR", "FAIL", "NOT RUN", "SKIP"] if status in statuses), "PASS")


def update_results(state):
    # Attempts are chronological; the latest retry determines each case result.
    latest = {attempt["case"]: attempt for attempt in state["attempts"]}
    for index, attempt in latest.items():
        state["results"][index] = case_status(attempt)


def step_failed(step):
    return step["status"] in {"FAIL", "ERROR"} or "FAIL" in [step.get(key) for key in ["files", "diagnostic", "visual"]]


def remove_attempts(state):
    """Remove only owned attempts, after the caller has stopped their Yazi."""
    for attempt in state["attempts"]:
        shutil.rmtree(owned(attempt["root"]))


def import_harness_errors(root, state):
    # Include old single-marker sessions; new guides append one JSON line per error.
    markers = []
    legacy = root / "manual-error.json"
    journal = root / "manual-errors.jsonl"
    if legacy.exists():
        markers.append(json.loads(read(legacy)))
    if journal.exists():
        markers.extend(json.loads(line) for line in read(journal).splitlines() if line.strip())
    history = state.setdefault("harness_errors", [])
    pending = markers[len(history):]
    for marker in pending:
        attempt = current(state)
        step = attempt["step"]
        try:
            origin, origin_step = map(int, marker.get("token").split(":"))
            if origin < 0 or origin_step < 0:
                raise ValueError("Negative error token")
            source = state["attempts"][origin]
            source["steps"][origin_step]
        except (AttributeError, TypeError, ValueError, IndexError):
            # Older or malformed markers cannot identify their originating step.
            pass
        else:
            attempt, step = source, origin_step
        attempt["steps"][step].update(status="ERROR", error=marker.get("error", "Guide error"))
        attempt["failed"] = True
        history.append(marker)
    if pending:
        save(root, state)


def view(state):
    attempt = current(state)
    spec = CASES[attempt["case"]]
    instruction = spec["steps"][attempt["step"]]
    unavailable = spec["optional"] == "git" and not state["git_plugin"]
    targets = Path(attempt["root"]) / "long.json"
    return dict(title=spec["title"], case=attempt["case"] + 1, total=len(CASES),
                step=attempt["step"] + 1, steps=len(spec["steps"]), instruction="SKIP: no --git-plugin supplied. W/n continues." if unavailable else instruction["do"],
                expect=instruction["expect"], command=instruction["command"], needs_baseline=bool(instruction["epoch"]),
                result=attempt["steps"][attempt["step"]],
                root=attempt["root"], opts=attempt["opts"], token=f'{state["active"]}:{attempt["step"]}',
                cases=[dict(title=c["title"], optional=c["optional"], result=state["results"][i]) for i, c in enumerate(CASES)],
                targets=json.loads(read(targets)) if targets.is_file() else [],
                finished=state.get("finished", False))


def start_case(root, state, index):
    if index < 0 or index >= len(CASES):
        raise ValueError("Invalid case index")
    spec = CASES[index]
    t = None
    try:
        write(root / "config/theme.toml", read(root / "baseline-theme.toml"))
        t = Runtime(state["git_plugin"], probe=False)
        write(t.root / "manual.json", json.dumps(dict(version=1, root=str(t.root), repo=str(REPO))))
        baseline(t)
        prepare(t, spec["setup"], root)
        opts = dict(command=str(t.root / "chezmoi-wrapper"), config=str(t.cfg), source=str(t.source),
                    destination=str(t.dest), persistent_state=str(t.root / "chezmoi.db"), cache=str(t.root / "cache/chezmoi"),
                    timeout=1, cache_ttl=spec["cache_ttl"], error_backoff=0.5)
        write(t.root / "attempt.json", json.dumps(dict(opts=opts)))
        attempt = dict(case=index, root=str(t.root), opts=opts, step=0,
                       steps=[dict(visual="unanswered", status="NOT RUN") for _ in spec["steps"]])
        if spec["optional"] == "git" and not state["git_plugin"]:
            for result in attempt["steps"]:
                result.update(status="SKIP", visual="SKIP", note="No --git-plugin supplied")
        prepare_step(root, attempt)
        state["attempts"].append(attempt)
        state["active"] = len(state["attempts"]) - 1
        state["finished"] = False
    except BaseException as error:
        if t is not None:
            t.close()
        if isinstance(error, Exception):
            raise PreparationError(index, 0, error) from error
        raise


def prepare_step(root, attempt):
    try:
        fixture = owned(attempt["root"])
        spec = CASES[attempt["case"]]["steps"][attempt["step"]]
        if spec["prep"]:
            prepare(context(fixture), spec["prep"], root)
        calls = fixture / "state/instrument/calls"
        attempt["call_offset"] = calls.stat().st_size if calls.exists() else 0
        attempt["epoch_before"] = None
    except Exception as error:
        raise PreparationError(attempt["case"], attempt["step"], error) from error


def initialize(root, git_plugin):
    git_plugin = str(Path(git_plugin).resolve(strict=True)) if git_plugin else None
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
        if calls.exists():
            with calls.open("rb") as log:
                log.seek(offset)
                for line in log:
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
    before = attempt.get("epoch_before")
    if spec["epoch"] == "same" and before is not None and snapshot.get("epoch") != before:
        diagnostic.append("Theme reload advanced status epoch")
    if spec["epoch"] == "advance" and (before is None or snapshot.get("epoch", -1) <= before):
        diagnostic.append("Press R to force a new status acquisition before recording PASS.")
    write(root / "snapshot.json", json.dumps(snapshot, indent=2))
    return dict(files="FAIL" if failures else "PASS", failures=failures,
                diagnostic="FAIL" if diagnostic else "PASS", diagnostic_failures=diagnostic)


def advance(root, state, snapshot):
    attempt = current(state)
    result = attempt["steps"][attempt["step"]]
    if result["visual"] not in {"PASS", "FAIL", "SKIP"}:
        result.update(check(state, snapshot))
        result["message"] = "Record visual PASS/FAIL or SKIP before advancing."
    elif attempt["step"] + 1 < len(attempt["steps"]):
        attempt["step"] += 1
        prepare_step(root, attempt)
    else:
        index = attempt["case"] + 1
        while index < len(CASES) and CASES[index]["optional"] == "git" and not state["git_plugin"]:
            state["results"][index] = "SKIP"
            state.setdefault("skip_reasons", {})[str(index)] = "No --git-plugin supplied"
            index += 1
        if index < len(CASES):
            start_case(root, state, index)
        else:
            state["finished"] = True


def transition(root, operation, payload):
    root, state = load(root)
    attempt = current(state)
    token = f'{state["active"]}:{attempt["step"]}'
    if payload.get("token") != token:
        raise StaleRequest("Stale guide request; reopen controls")
    import_harness_errors(root, state)
    snapshot = payload.get("snapshot", {})
    result = attempt["steps"][attempt["step"]]
    result.pop("message", None)
    if CASES[attempt["case"]]["optional"] == "git" and not state["git_plugin"] and operation in {"check", "pass", "fail", "accept"}:
        save(root, state)
        return view(state)
    if operation in {"check", "pass", "fail", "accept"}:
        result.pop("error", None)
        result.update(check(state, snapshot))
        if operation != "check":
            result["visual"] = "FAIL" if operation == "fail" else "PASS"
            result["note"] = payload.get("note", "")
        if "FAIL" in [result["files"], result["diagnostic"], result["visual"]]:
            result["status"] = "FAIL"
        elif result["visual"] in {"PASS", "SKIP"}:
            result["status"] = result["visual"]
        else:
            result["status"] = "NOT RUN"
        if operation == "accept":
            save(root, state)
            if result["status"] == "PASS":
                advance(root, state, snapshot)
            else:
                failures = result["failures"] + result["diagnostic_failures"]
                result["message"] = "Checks failed; staying on this step: " + "; ".join(failures[:2]) + ". W/d: details; W/n: continue after failure."
    elif operation == "baseline":
        attempt["epoch_before"] = snapshot.get("epoch")
    elif operation == "skip":
        result.update(status="SKIP", visual="SKIP", note=payload.get("note") or "Skipped by tester")
    elif operation == "next":
        advance(root, state, snapshot)
    elif operation in {"restart", "jump"}:
        start_case(root, state, attempt["case"] if operation == "restart" else int(payload["index"]))
    elif operation == "finish":
        state["exit"] = dict(keep=payload.get("keep", True))
    else:
        raise ValueError(f"Unknown guide operation: {operation}")
    attempt = current(state)
    if any(step_failed(step) for step in attempt["steps"]):
        attempt["failed"] = True
    save(root, state)
    return view(state)


def details(root):
    root, state = load(root)
    attempt = current(state)
    fixture = owned(attempt["root"])
    spec = CASES[attempt["case"]]
    lines = [f'{spec["title"]} - step {attempt["step"] + 1}/{len(spec["steps"])}', "",
             "DO: " + spec["steps"][attempt["step"]]["do"], "", "EXPECT: " + spec["steps"][attempt["step"]]["expect"], "",
             "COMMAND: " + spec["steps"][attempt["step"]]["command"], "",
             "Signs are MXYD (plus leading separator). C=managed; XY=chezmoi status; *=directory change; !=failure.",
             "Spaces are significant: clean='C   ', local='CMM ', source='C M ', unmanaged='    '.", "",
             "CURRENT RESULT", json.dumps(attempt["steps"][attempt["step"]], indent=2), "",
             "CASES"]
    if state.get("finished"):
        lines = ["Walk complete - saved case verdicts", "", "CASES"]
    lines += [f'{i + 1:2}. {c["title"]}: {state["results"][i]}' for i, c in enumerate(CASES)]
    if state.get("preparation_errors"):
        lines += ["", "PREPARATION ERRORS"]
        for error in state["preparation_errors"]:
            title = CASES[error["case"]]["title"]
            lines.append(f'{error["operation"]}: case {error["case"] + 1} ({title}), step {error["step"] + 1}: {error["error"]}')
    lines += ["", "EXECUTED ACTIONS (argv and exit code; background queries excluded)"]
    actions = fixture / "state/instrument/actions.jsonl"
    lines += read(actions).splitlines() if actions.exists() else ["No interactive chezmoi command executed in this attempt."]
    lines += ["", "VERSIONS", json.dumps(state["versions"], indent=2), "", f"Fixture: {fixture}"]
    for relative in ["snapshot.json", "state/instrument/calls", "editor-targets.json"]:
        path = fixture / relative
        if path.is_file():
            lines += ["", relative, read(path)[-24000:]]
    lines += ["", "SOURCE / DEST CONTENTS (JSON escaped; at most 80 files per tree)"]
    for directory in [Path(attempt["opts"]["source"]), fixture / "dest"]:
        for path in heapq.nsmallest(80, directory.rglob("*")):
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
    import_harness_errors(root, state)
    update_results(state)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    archive = REPO / ".dev/manual-runs" / stamp
    archive.mkdir(parents=True)
    write(archive / "results.json", json.dumps(state, indent=2))
    for i, attempt in enumerate(state["attempts"]):
        fixture = owned(attempt["root"])
        directory = archive / f"attempt-{i + 1}"
        directory.mkdir()
        for relative in ["snapshot.json", "initial.diff", "state/instrument/calls", "state/instrument/actions.jsonl", "editor-targets.json", "attempt.json"]:
            path = fixture / relative
            if path.is_file():
                target = directory / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
    shutil.copytree(root / "state", archive / "session-state")
    for name in ["manual-error.json", "manual-errors.jsonl"]:
        if (root / name).exists():
            shutil.copyfile(root / name, archive / name)
    failed = bool(state["harness_errors"]) or bool(state.get("preparation_errors")) or any(
        attempt.get("failed") or any(step_failed(step) for step in attempt["steps"])
        for attempt in state["attempts"])
    keep = state.get("exit", {}).get("keep", True) or failed
    print(f"Results: {archive / 'results.json'}")
    if keep:
        print(f"Fixtures retained: {root}")
    else:
        remove_attempts(state)
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
        except StaleRequest as error:
            _, state = load(root)
            value = view(state)
            value["result"] = dict(value["result"], message=str(error))
        except PreparationError as error:
            _, state = load(root)
            value = view(state)
            state.setdefault("preparation_errors", []).append(dict(
                operation=args.operation, token=value["token"], case=error.case, step=error.step, error=str(error)))
            save(root, state)
            message = f"Could not prepare case {error.case + 1}, step {error.step + 1}: {error}. W/d: details; retry the operation."
            value["result"] = dict(value["result"], message=message)
        except Exception as error:
            _, state = load(root)
            attempt = current(state)
            attempt["steps"][attempt["step"]].update(status="ERROR", error=str(error))
            attempt["failed"] = True
            save(root, state)
            value = view(state)
        print(json.dumps(value))


if __name__ == "__main__":
    main()
