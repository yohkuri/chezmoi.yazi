"""Disposable interactive editor double; never used outside a test fixture."""
import json
from pathlib import Path
import select
import sys
import tty
from support import read, write

root = Path(sys.argv[1])
targets = [Path(arg) for arg in sys.argv[2:]]
write(root / "editor-targets.json", json.dumps(list(map(str, targets))))
mode = read(root / "editor-mode")
if mode == "manual":
    print("Disposable fixture editor. Personal editor/config is not used.")
    for target in targets:
        print(f"{json.dumps(target.name, ensure_ascii=False)}: {read(target)!r}")
    print("Type one line and Enter to save to all selected source files; Ctrl-C cancels.", flush=True)
    value = input("New source content > ")
elif mode == "terminal":
    # Leave what a careless command can: a color, a raw terminal, and a key
    # typed while it ran, still queued. Raw mode is set first, since setting
    # it drops what is queued; then wait for the test's key without reading it.
    tty.setraw(sys.stdin.fileno())
    print("\x1b[41mFixture editor left the terminal raw.", end="\r\n", flush=True)
    select.select([sys.stdin], [], [])
    value = "edited by fixture"
elif mode == "wait":
    print("Fixture editor input:", flush=True)
    value = input()
else:
    value = "edited by fixture"
for target in targets:
    write(target, value + "\n")
    if mode == "partial-fail":
        sys.exit(1)
