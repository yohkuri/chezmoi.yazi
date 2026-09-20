"""Fast checks for the harness's byte handling and cleanup boundaries."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from support import REPO, lua, owned, read, run, stop, write


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

    def test_process_timeout(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            run([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.05)


if __name__ == "__main__":
    unittest.main()
