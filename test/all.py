#!/usr/bin/env -S uv run --locked
"""Run test/check.py and the runtime, E2E and guide suites at once.

The Yazi-driven suites spend most of their time waiting on the screen, so
together they take about as long as the guide alone. Each suite's output is
printed whole when it ends, so the outputs do not mix. Run one at a time, and
no other guide run or walk meanwhile: the guide's foreground launcher check
expects one new report in .dev/manual-runs, so another one finishing fails it.

Ctrl-C in the terminal reaches the suites too; this waits while they clean up,
prints what they printed and exits 130. A SIGINT sent to this process alone
is not passed on, since the suites would get a second one from a terminal.
"""
import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from support import REPO

SUITES = ["check.py", "runtime.py", "e2e.py", "manual_runtime.py"]


def run(root, name):
    start = time.monotonic()
    try:
        # Unbuffered, a suite's stdout and stderr keep their order in the one pipe.
        result = subprocess.run([root / "test" / name], cwd=root, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                env={**os.environ, "PYTHONUNBUFFERED": "1"})
        # Decoded here rather than by text=True, which follows the locale and turns a lone \r into \n.
        code, output = result.returncode, result.stdout.decode(errors="replace")
    except OSError as error:
        code, output = 1, f"Could not start test/{name}: {error}\n"
    return name, code, output, time.monotonic() - start


def report(future):
    name, code, output, seconds = future.result()
    print(f"==> test/{name}")
    print(output, end="" if output.endswith("\n") or not output else "\n")
    print(f"<== test/{name}: {'PASS' if code == 0 else f'FAIL ({code})'} in {seconds:.0f} s\n", flush=True)


def main(root=REPO, suites=SUITES):
    interrupted = False
    with ThreadPoolExecutor(len(suites)) as pool:
        futures = [pool.submit(run, root, name) for name in suites]
        pending = set(futures)
        try:
            for future in as_completed(futures):
                report(future)
                # Only once it is whole: a block that Ctrl-C cut short is printed again.
                pending.discard(future)
        except KeyboardInterrupt:
            interrupted = True
            print("Interrupted; waiting for the suites to stop", flush=True)
            for future in as_completed(pending):
                report(future)
    codes = [future.result()[1] for future in futures]
    for name, code in zip(suites, codes):
        print(f"{'PASS' if code == 0 else 'FAIL'} test/{name}")
    # 130 is what uv returns for a suite that Ctrl-C ended, so an interrupted run does not look like a failure.
    return 130 if interrupted else 1 if any(codes) else 0


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    sys.exit(main())
