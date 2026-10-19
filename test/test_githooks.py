"""The hooks in .githooks refuse a commit on main and a push to it, here only."""
import subprocess
import tempfile
import unittest
from support import REPO
from test_skills import ISOLATED, git

HOOKS = REPO / ".githooks"
THIS = [
    "https://github.com/yohkuri/chezmoi.yazi",
    "https://github.com/yohkuri/chezmoi.yazi.git",
    "https://GitHub.com/Yohkuri/Chezmoi.yazi/",
    "git@github.com:yohkuri/chezmoi.yazi.git",
    "ssh://git@github.com/yohkuri/chezmoi.yazi.git",
    "ssh://git@ssh.github.com:443/yohkuri/chezmoi.yazi.git",
]
OTHER = [
    "https://github.com/someone/chezmoi.yazi.git",
    "https://github.com/yohkuri/chezmoi.yazi-fork",
    "https://notgithub.com/yohkuri/chezmoi.yazi",
    "/srv/mirror/chezmoi.yazi.git",
]


def hook(name, *args, cwd, stdin="", **env):
    return subprocess.run([HOOKS / name, *args], cwd=cwd, env=dict(ISOLATED, **env), input=stdin,
                          capture_output=True, text=True, timeout=10)


class PreCommitTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = directory.name
        git(self.root, "-c", "init.templateDir=", "init", "--quiet", env=ISOLATED)

    def commit(self, origin=None, branch="main", **env):
        git(self.root, "symbolic-ref", "HEAD", f"refs/heads/{branch}", env=ISOLATED)
        if origin is not None:
            git(self.root, "config", "remote.origin.url", origin, env=ISOLATED)
        return hook("pre-commit", cwd=self.root, **env)

    def test_refuses_main_of_this_repository(self):
        for url in THIS:
            with self.subTest(url=url):
                result = self.commit(url)
                self.assertEqual(result.returncode, 1)
                self.assertIn("refusing a commit on `main`", result.stderr)

    def test_refuses_main_without_origin(self):
        self.assertEqual(self.commit().returncode, 1)

    def test_allows_other_repositories(self):
        for url in OTHER:
            with self.subTest(url=url):
                self.assertEqual(self.commit(url).returncode, 0)

    def test_allows_other_branches(self):
        self.assertEqual(self.commit(THIS[0], "fix/main").returncode, 0)

    def test_allows_a_detached_head(self):
        git(self.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "--allow-empty",
            "--no-verify", "-m", "x", env=ISOLATED)
        git(self.root, "switch", "--quiet", "--detach", env=ISOLATED)
        git(self.root, "config", "remote.origin.url", THIS[0], env=ISOLATED)
        self.assertEqual(hook("pre-commit", cwd=self.root).returncode, 0)

    def test_override(self):
        for value, code in [("1", 0), ("yes", 0), ("0", 1), ("false", 1), ("no", 1), ("", 1)]:
            with self.subTest(value=value):
                self.assertEqual(self.commit(THIS[0], CHEZMOI_YAZI_COMMIT_ON_MAIN=value).returncode, code)


class PrePushTests(unittest.TestCase):
    def push(self, url, *refs):
        with tempfile.TemporaryDirectory() as directory:
            lines = "".join(f"refs/heads/x {'1' * 40} {ref} {'0' * 40}\n" for ref in refs)
            return hook("pre-push", "origin", url, cwd=directory, stdin=lines)

    def test_refuses_main_on_this_repository(self):
        for url in [*THIS, ""]:
            with self.subTest(url=url):
                result = self.push(url, "refs/heads/fix/a", "refs/heads/main")
                self.assertEqual(result.returncode, 1)
                self.assertIn("refusing a push to `main`", result.stderr)

    def test_allows_other_repositories(self):
        for url in OTHER:
            with self.subTest(url=url):
                self.assertEqual(self.push(url, "refs/heads/main").returncode, 0)

    def test_allows_other_refs(self):
        for refs in [(), ("refs/heads/fix/main",), ("refs/tags/main",), ("refs/heads/main-notes",)]:
            with self.subTest(refs=refs):
                self.assertEqual(self.push(THIS[0], *refs).returncode, 0)


if __name__ == "__main__":
    unittest.main()
