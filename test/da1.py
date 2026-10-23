"""Answer Yazi's terminal probe for the fixture's tmux, which has no terminal.

`Runtime.session` runs this under `pipe-pane -IO`: stdin is the pane's output
and stdout is typed into the pane. Once tmux names itself, Yazi re-sends DA1
through tmux passthrough, and before each hide or quit it waits up to 5 s for
the reply (yazi-emulator/src/probe.rs in Yazi 26.9.1). Answer only that query,
and record each answer so that a Yazi that changes it fails the harness.
"""
import os
import sys

QUERY = b"\x1bPtmux;\x1b\x1b[0c"
REPLY = b"\x1b[?62;22c"


def answer(data):
    """Return how many whole queries data holds and the tail to keep for the next read."""
    # A query split across reads ends in the tail; an answered one cannot recur in it.
    return data.count(QUERY), data[1 - len(QUERY):]


if __name__ == "__main__":
    replies = sys.argv[1]
    tail = b""
    while chunk := os.read(0, 65536):
        count, tail = answer(tail + chunk)
        if count:
            # Record first, so that no check can see Yazi answered but no record.
            with open(replies, "a") as stream:
                stream.write("DA1\n" * count)
            os.write(1, REPLY * count)
