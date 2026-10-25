"""Checks for how test/all.py reports suites that run at once."""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import all as runner
from support import write


class AllTests(unittest.TestCase):
    def main(self, scripts):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "test").mkdir()
            for name, body in scripts.items():
                path = root / "test" / name
                write(path, body if body.startswith("#!") else "#!/bin/sh\n" + body + "\n")
                path.chmod(0o644 if name.startswith("unrunnable") else 0o755)
            output = io.StringIO()
            # Under test/all.py this test inherits PYTHONUNBUFFERED=1, which would hide the runner's own.
            with contextlib.redirect_stdout(output), mock.patch.dict(os.environ):
                os.environ.pop("PYTHONUNBUFFERED", None)
                code = runner.main(root, list(scripts))
        return code, output.getvalue()

    def test_prints_each_suite_whole_in_the_order_they_end(self):
        # slow.py goes on only after fails.py has written its line, and keeps
        # running a while after, so fails.py ends first; it gives up after 5 s
        # rather than hang if the scripts ever run one after the other.
        slow = ("echo one; i=0; until [ -e ended ]; do i=$((i + 1)); [ $i -gt 100 ] && exit 9; sleep 0.05; done; "
                "sleep 1; echo two")
        code, output = self.main({"slow.py": slow, "fails.py": "echo broken >&2; touch ended; exit 3"})
        lines = output.splitlines()
        self.assertEqual(code, 1)
        self.assertEqual(lines[:2], ["==> test/fails.py", "broken"])
        self.assertTrue(lines[2].startswith("<== test/fails.py: FAIL (3) in "), lines)
        self.assertEqual(lines[4:7], ["==> test/slow.py", "one", "two"])
        self.assertTrue(lines[7].startswith("<== test/slow.py: PASS in "), lines)
        self.assertEqual(lines[-2:], ["PASS test/slow.py", "FAIL test/fails.py"])

    def test_passes_only_when_every_suite_passes(self):
        code, output = self.main({"a.py": "true", "b.py": "true"})
        self.assertEqual(code, 0)
        self.assertEqual(output.splitlines()[-2:], ["PASS test/a.py", "PASS test/b.py"])

    def test_keeps_a_suites_order_and_reports_the_others_when_one_cannot_start(self):
        # The interpreter is quoted for sh, since a shebang cannot hold a path with a space.
        python = (f"exec '{sys.executable}' - <<'EOF'\nimport sys\n"
                  "print('first'); print('second', file=sys.stderr); print('third', end='')\nEOF")
        code, output = self.main({"python.py": python, "bytes.py": r"printf 'bad \377\rsame line\n'",
                                  "unrunnable.py": "true"})
        self.assertEqual(code, 1)
        self.assertIn("first\nsecond\nthird\n<== test/python.py: PASS", output)
        self.assertIn("bad �\rsame line\n<== test/bytes.py: PASS", output)
        self.assertIn("Could not start test/unrunnable.py", output)
        self.assertEqual(output.splitlines()[-3:],
                         ["PASS test/python.py", "PASS test/bytes.py", "FAIL test/unrunnable.py"])


if __name__ == "__main__":
    unittest.main()
