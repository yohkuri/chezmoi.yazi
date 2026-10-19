"""Every skill file under .agents/skills is reachable from .claude/skills."""
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from support import REPO, run, write

HOW = """Claude Code reads skills from .claude/skills. Give each file under
.agents/skills a relative symlink at the same path there, one per file:
`ya pkg add` refuses a symlink to a directory and then installs nothing.
  mkdir -p DIR && ln -sfn TARGET LINK
"""
# A hook or `git rebase -x` sets GIT_DIR or GIT_INDEX_FILE, which would point
# these commands at the caller's repository instead of the one named by cwd.
ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def git(root, *args):
    return run(["git", *args], cwd=root, env=ENV)


def listed(root, path):
    # Untracked files count, so a new skill is checked before it is committed;
    # ignored ones do not, since a clone would not have them.
    out = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", path)
    return [Path(name) for name in out.split("\0") if name]


def problems(root):
    root = Path(root)
    sources = listed(root, ".agents/skills")
    found, dirs = [], set()

    def under_dir_link(link):
        for path in [link, *link.parents]:
            if path.parts[:2] != (".claude", "skills"):
                break
            if (root / path).is_symlink() and (root / path).is_dir():
                if path not in dirs:
                    dirs.add(path)
                    found.append(f"{path}: a symlink to a directory; remove it and link each file")
                return True
        return False

    for source in sources:
        link = Path(".claude/skills", *source.parts[2:])
        target = os.path.relpath(source, link.parent)
        if under_dir_link(link):
            continue
        actual = os.readlink(root / link) if (root / link).is_symlink() else None
        if actual != target:
            found.append(f"{link}: must be a symlink to {target}, not {actual or 'missing or a copy'}")
    for link in listed(root, ".claude/skills"):
        source = Path(".agents/skills", *link.parts[2:])
        if not under_dir_link(link) and source not in sources:
            found.append(f"{link}: nothing listed at {source} for it to point at")
    return sources, found


class SkillLinkTests(unittest.TestCase):
    def test_repository(self):
        sources, found = problems(REPO)
        self.assertTrue(sources, "No skill files listed under .agents/skills")
        self.assertEqual(found, [], HOW + "\n".join(found))

    def test_reports_each_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "-c", "init.templateDir=", "init", "--quiet")
            names = ["ok.md", "my notes.md", "日本語.md", "missing.md", "copy.md", "wrong.md"]
            for skill in "ab":
                (root / ".agents/skills" / skill).mkdir(parents=True)
                for name in names:
                    write(root / ".agents/skills" / skill / name, "x\n")
            write(root / ".gitignore", "/.agents/skills/a/ignored.md\n")
            write(root / ".agents/skills/a/ignored.md", "x\n")
            (root / ".claude/skills/a").mkdir(parents=True)
            for name in ["ok.md", "my notes.md", "日本語.md", "ignored.md", "gone.md"]:
                (root / ".claude/skills/a" / name).symlink_to(f"../../../.agents/skills/a/{name}")
            shutil.copy(root / ".agents/skills/a/copy.md", root / ".claude/skills/a/copy.md")
            (root / ".claude/skills/a/wrong.md").symlink_to("../../.agents/skills/a/wrong.md")
            (root / ".claude/skills/b").symlink_to("../../.agents/skills/b")
            # Staged and untracked files are both listed.
            git(root, "add", ".agents/skills/a", ".claude/skills/a/ok.md")
            sources, found = problems(root)
            self.assertIn(Path(".agents/skills/a/ok.md"), sources)
            self.assertEqual(sorted(found), [
                ".claude/skills/a/copy.md: must be a symlink to ../../../.agents/skills/a/copy.md, "
                "not missing or a copy",
                ".claude/skills/a/gone.md: nothing listed at .agents/skills/a/gone.md for it to point at",
                ".claude/skills/a/ignored.md: nothing listed at .agents/skills/a/ignored.md for it to point at",
                ".claude/skills/a/missing.md: must be a symlink to ../../../.agents/skills/a/missing.md, "
                "not missing or a copy",
                ".claude/skills/a/wrong.md: must be a symlink to ../../../.agents/skills/a/wrong.md, "
                "not ../../.agents/skills/a/wrong.md",
                ".claude/skills/b: a symlink to a directory; remove it and link each file",
            ])

    def test_reports_a_linked_skills_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "-c", "init.templateDir=", "init", "--quiet")
            (root / ".agents/skills/a").mkdir(parents=True)
            write(root / ".agents/skills/a/SKILL.md", "x\n")
            (root / ".claude").mkdir()
            (root / ".claude/skills").symlink_to("../.agents/skills")
            self.assertEqual(problems(root)[1], [
                ".claude/skills: a symlink to a directory; remove it and link each file"])


if __name__ == "__main__":
    unittest.main()
