"""Disposable interactive editor double; never used outside a test fixture."""
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
targets = [Path(arg) for arg in sys.argv[2:]]
(root / "editor-targets.json").write_text(json.dumps(list(map(str, targets))))
mode = (root / "editor-mode").read_text()
if mode == "wait":
    print("Fixture editor input:", flush=True)
    value = input()
else:
    value = "edited by fixture"
for target in targets:
    target.write_text(value + "\n")
    if mode == "partial-fail":
        sys.exit(1)
