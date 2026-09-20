#!/usr/bin/env -S uv run --locked
"""Measure the three CLI commands for one ordinary recursive scope."""
import time
from support import fixture, write

for count in [100, 5000]:
    with fixture() as t:
        directory = t.source / "dot_config"
        directory.mkdir()
        (t.dest / ".config").mkdir()
        for index in range(count):
            write(directory / f"file-{index:05d}", "fixture\n")
        before = time.monotonic()
        t.chezmoi("execute-template", "{{ .chezmoi.destDir }}")
        managed = t.chezmoi("managed", "--include=all", "--exclude=none", "--path-style=absolute", "--nul-path-separator")
        status = t.chezmoi("status", "--include=all", "--exclude=none", "--path-style=absolute",
                           "--recursive=true", "--", t.dest / ".config")
        elapsed = time.monotonic() - before
        assert managed.count('\0') == count + 1
        assert status.count('\n') == count
        size = len(managed.encode()) + len(status.encode())
        print(f"{count} files: 3 subprocesses, {elapsed:.3f} s, {size} output bytes")
