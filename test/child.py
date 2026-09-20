"""Real child processes for testing Yazi's process adapter."""
import os
from pathlib import Path
import sys
import time

mode, pid_file = sys.argv[1:]
Path(pid_file).write_text(str(os.getpid()))
if mode == "closed":
    os.close(1)
elif mode == "stderr":
    sys.stderr.buffer.write(b"x" * 262144)
    sys.stderr.buffer.flush()
    sys.stdout.buffer.write(b"ab")
    sys.stdout.buffer.flush()
    time.sleep(0.05)
    sys.stdout.buffer.write(b"cd\0ok\n")
    sys.stdout.buffer.flush()
    sys.exit(0)
elif mode == "partial":
    sys.stdout.buffer.write(b"unfinished")
    sys.stdout.buffer.flush()
time.sleep(10)
