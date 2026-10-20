"""The Claude Code Lua hook reads the StyLua pin from mise.toml."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from support import REPO, write
from test_skills import ISOLATED, git

HOOK = REPO / "scripts/format-lua-hook.sh"
# Stands in for StyLua: reports $VERSION and records where and how it formatted.
FAKE = """#!/bin/sh
[ "$1" = --version ] && { echo "stylua $VERSION"; exit; }
printf '%s\\n' "$(pwd -P)" "$*" > "$CALLED"
"""


@unittest.skipUnless(shutil.which("jq"), "the hook needs jq")
class FormatHookTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name).resolve()
        self.root = self.tmp / "repo"
        self.root.mkdir()
        git(self.root, "-c", "init.templateDir=", "init", "--quiet", env=ISOLATED)
        (self.root / "sub").mkdir()
        write(self.root / "sub/a.lua", "return 1\n")
        (self.tmp / "bin").mkdir()
        write(self.tmp / "bin/stylua", FAKE)
        (self.tmp / "bin/stylua").chmod(0o755)

    def hook(self, pins, version):
        write(self.root / "mise.toml", pins)
        payload = json.dumps({"tool_input": {"file_path": str(self.root / "sub/a.lua")}})
        env = dict(ISOLATED, CLAUDE_PROJECT_DIR=str(self.root), VERSION=version,
                   CALLED=str(self.tmp / "called"), PATH=f"{self.tmp / 'bin'}{os.pathsep}{os.environ['PATH']}")
        # Run from elsewhere, as a session working in another checkout would.
        return subprocess.run(["sh", HOOK], cwd=self.tmp, env=env, input=payload,
                              capture_output=True, text=True, timeout=10)

    def test_reads_this_repository_pin(self):
        result = self.hook((REPO / "mise.toml").read_text(), "0.0.0")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertRegex(result.stderr, r"StyLua 0\.0\.0 is installed, but CI uses \d+\.\d+\.\d+\.")

    def test_formats_from_the_file_checkout_when_the_pin_matches(self):
        for pins in ['stylua = "9.9.9"\n', 'stylua="9.9.9"  # formatter\n']:
            with self.subTest(pins=pins):
                (self.tmp / "called").unlink(missing_ok=True)
                self.assertEqual(self.hook(pins, "9.9.9").returncode, 0)
                self.assertEqual((self.tmp / "called").read_text().splitlines(),
                                 [str(self.root), "--config-path .stylua.toml -- sub/a.lua"])

    def test_refuses_without_a_pin(self):
        for pins in ['lua = "5.5.1"\n', '# stylua = "9.9.9"\n']:
            with self.subTest(pins=pins):
                result = self.hook(pins, "9.9.9")
                self.assertEqual(result.returncode, 2)
                self.assertIn("could not read the stylua version", result.stderr)


if __name__ == "__main__":
    unittest.main()
