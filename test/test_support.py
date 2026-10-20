"""Fast checks for the harness's byte handling and cleanup boundaries."""
import errno
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from support import QUERY_FLAGS, REPO, Runtime, check_call, lua, owned, read, run, stop, write


class SupportTests(unittest.TestCase):
    def test_lua_string_roundtrip(self):
        value = 'space " quote \\ slash\r\n日本語\0end'
        result = subprocess.run(["lua", "-e", "io.write(" + lua(value) + ")"],
                                capture_output=True, check=True, timeout=5)
        self.assertEqual(result.stdout, value.encode())

    def test_binary_text_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data"
            write(path, "a\r\nb\0c")
            self.assertEqual(read(path), "a\r\nb\0c")

    def test_owned_marker_and_symlink(self):
        with tempfile.TemporaryDirectory(prefix="chezmoi-yazi-test-") as directory:
            root = Path(directory).resolve()
            with self.assertRaises(FileNotFoundError):
                owned(root)
            marker = root / "manual.json"
            write(marker, json.dumps(dict(version=1, root=str(root), repo=str(REPO))))
            self.assertEqual(owned(root), root)
            write(marker, json.dumps(dict(version=1, root="/", repo=str(REPO))))
            with self.assertRaises(AssertionError):
                owned(root)
            link = root / "alias"
            link.symlink_to(root)
            with self.assertRaises(AssertionError):
                owned(link)
            (root / "tmux.sock").symlink_to(marker)
            with self.assertRaises(AssertionError):
                stop(root)
            self.assertTrue(marker.exists())

    def test_check_call(self):
        context = ["--config", "/c", "--cache", "/k"]
        status = [*QUERY_FLAGS, *context, "status", "--include=all", "--exclude=none", "--", "/d/a"]
        narrow = [*QUERY_FLAGS, *context, "managed", "--include=dirs", "--exclude=externals"]
        action = [*context, "apply", "--include=all", "--exclude=none", "--recursive=true", "--", "/d/a"]
        self.assertTrue(check_call(status) and check_call(narrow))
        self.assertFalse(check_call(action))
        for args in [status[1:], [*QUERY_FLAGS[:-1], *context, "status", QUERY_FLAGS[-1], *status[-4:]],
                     [*status[:-3], "--exclude=encrypted", *status[-2:]],
                     [*status[:-4], "--", "--include=all", "--exclude=none", "/d/a"],
                     [*status[:-2], "--include=all", *status[-2:]],
                     [*narrow[:-1], "--exclude=none"], [*action, "--force=true"],
                     [*status[:-2], "-x", "encrypted", *status[-2:]],
                     [*status[:-2], "--exclude", "encrypted", *status[-2:]],
                     [*QUERY_FLAGS, *context, "--include=all", "--exclude=none", "status", "--", "/d/a"],
                     [*status[:-2], "--color=true", *status[-2:]],
                     [*QUERY_FLAGS, *context, "source-path", "--", "/d/a"],
                     [*QUERY_FLAGS, *context], [*context, "remove", "--", "/d/a"]]:
            with self.subTest(args=args), self.assertRaises(AssertionError):
                check_call(args)

    def test_process_timeout(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            run([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.05)

    def test_cleanup_retries_transient_nonempty_directory(self):
        root = Path(tempfile.mkdtemp(prefix="chezmoi-yazi-test-")).resolve()
        instance = Runtime.__new__(Runtime)
        instance.root = instance.owned_root = root
        instance.started = instance.keep = False
        actual_rmtree = shutil.rmtree
        attempts = 0

        def remove(path):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise OSError(errno.ENOTEMPTY, "writer raced with cleanup", path)
            actual_rmtree(path)

        try:
            with mock.patch("support.shutil.rmtree", side_effect=remove), mock.patch("support.time.sleep"):
                instance.close()
            self.assertEqual(attempts, 2)
            self.assertFalse(root.exists())
        finally:
            if root.exists():
                actual_rmtree(root)


if __name__ == "__main__":
    unittest.main()
