"""Instrument only the fixture's chezmoi subprocesses."""
import json
from pathlib import Path
import subprocess
import sys
import time

root, chezmoi, *args = sys.argv[1:]
root = Path(root)
with (root / "calls").open("a") as stream:
    stream.write(json.dumps(args) + "\n")
control = root / "control"
mode = control.read_text() if control.exists() else ""
if "managed" in args and mode == "fail-managed":
    sys.exit(1)
if "--no-tty" not in args:
    # Explicit actions must retain their real terminal and have no query deadline.
    sys.exit(subprocess.run([chezmoi, *args]).returncode)
try:
    result = subprocess.run([chezmoi, *args], capture_output=True, timeout=10)
except subprocess.TimeoutExpired:
    sys.exit(124)
if "status" in args and mode == "slow":
    (root / "barrier").write_text("ready")
    time.sleep(0.5)
sys.stdout.buffer.write(result.stdout)
sys.stdout.buffer.flush()
sys.exit(result.returncode)
