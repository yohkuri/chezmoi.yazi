#!/usr/bin/env -S uv run --locked
"""Run the local development checks from the repository root."""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.exit(subprocess.run(["npm", "run", "check"],
                            cwd=Path(__file__).resolve().parents[1]).returncode)
