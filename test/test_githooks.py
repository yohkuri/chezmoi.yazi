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
    # An override exported in the developer's shell must not decide the result.
    env = {**ISOLATED, "CHEZMOI_YAZI_COMMIT_ON_MAIN": "", **env}
    return subprocess.run([HOOKS / name, *args], cwd=cwd, env=env, input=stdin,
                          capture_output=True, text=True, timeout=10)


class PreCommitTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = directory.name
        self.git("-c", "init.templateDir=", "init", "--quiet")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "--allow-empty", "-m", "x")

    def git(self, *args):
        return git(self.root, *args, env=ISOLATED)

    def commit(self, origin=None, branch="main", **env):
        """Run the hook on branch, or on a detached HEAD for None."""
        if branch:
            self.git("symbolic-ref", "HEAD", f"refs/heads/{branch}")
        else:
            self.git("switch", "--quiet", "--detach")
        if origin is not None:
            self.git("config", "remote.origin.url", origin)
        return hook("pre-commit", cwd=self.root, **env)

    def test_refuses_main_of_this_repository(self):
        for url in THIS:
            with self.subTest(url=url):
                result = self.commit(url)
                self.assertEqual(result.returncode, 1)
                self.assertIn("refusing a commit on `main`", result.stderr)

    def test_refuses_main_beside_a_tag_named_main(self):
        self.git("tag", "main")
        self.assertEqual(self.commit(THIS[0]).returncode, 1)

    def test_allows_no_origin(self):
        self.assertEqual(self.commit().returncode, 0)

    def test_allows_other_repositories(self):
        for url in OTHER:
            with self.subTest(url=url):
                self.assertEqual(self.commit(url).returncode, 0)

    def test_allows_other_branches(self):
        self.assertEqual(self.commit(THIS[0], "fix/main").returncode, 0)

    def test_allows_a_detached_head(self):
        self.assertEqual(self.commit(THIS[0], None).returncode, 0)

    def test_override(self):
        self.commit(THIS[0])
        for value, code in [("1", 0), ("yes", 1), ("true", 1), ("0", 1), ("FALSE", 1), ("off", 1), ("", 1)]:
            with self.subTest(value=value):
                result = hook("pre-commit", cwd=self.root, CHEZMOI_YAZI_COMMIT_ON_MAIN=value)
                self.assertEqual(result.returncode, code)


class PrePushTests(unittest.TestCase):
    def push(self, url, *refs, local="refs/heads/x"):
        with tempfile.TemporaryDirectory() as directory:
            lines = "".join(f"{local} {'1' * 40} {ref} {'0' * 40}\n" for ref in refs)
            return hook("pre-push", "origin", url, cwd=directory, stdin=lines)

    def test_refuses_main_on_this_repository(self):
        for url in THIS:
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

    def test_allows_pushing_local_main_elsewhere(self):
        self.assertEqual(self.push(THIS[0], "refs/heads/fix/a", local="refs/heads/main").returncode, 0)


if __name__ == "__main__":
    unittest.main()
