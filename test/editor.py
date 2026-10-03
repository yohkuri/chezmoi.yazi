"""Disposable interactive editor double; never used outside a test fixture."""
import json
from pathlib import Path
import sys
from support import read, write

root = Path(sys.argv[1])
targets = [Path(arg) for arg in sys.argv[2:]]
write(root / "editor-targets.json", json.dumps(list(map(str, targets))))
mode = read(root / "editor-mode")
if mode == "manual":
    print("Disposable fixture editor. Personal editor/config is not used.")
    for target in targets:
        print(f"{target.name}: {read(target)!r}")
    print("Type one line and Enter to save to all selected source files; Ctrl-C cancels.", flush=True)
    value = input("New source content > ")
elif mode == "wait":
    print("Fixture editor input:", flush=True)
    value = input()
else:
    value = "edited by fixture"
for target in targets:
    write(target, value + "\n")
    if mode == "partial-fail":
        sys.exit(1)
