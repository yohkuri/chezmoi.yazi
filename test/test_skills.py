"""Every skill file under .agents/skills is reachable from .claude/skills."""
import os
from pathlib import Path
import unittest
from support import REPO, run

HOW = """Claude Code reads skills from .claude/skills. Give each file under
.agents/skills a relative symlink at the same path there, one per file:
`ya pkg add` refuses a symlink to a directory and then installs nothing.
  mkdir -p DIR && ln -sfn TARGET LINK
"""
# A hook or `git rebase -x` sets GIT_DIR or GIT_INDEX_FILE, which would point
# these commands at the caller's repository instead of the one named by cwd.
ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def listed(path):
    # Untracked files count, so a new skill is checked before it is committed;
    # ignored ones do not, since a clone would not have them.
    out = run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", path], cwd=REPO, env=ENV)
    return {Path(name) for name in out.split("\0") if name}


def problems():
    sources = listed(".agents/skills")
    links = listed(".claude/skills")
    found, dirs = [], set()

    def under_dir_link(link):
        for path in [link, *link.parents]:
            if path.parts[:2] != (".claude", "skills"):
                break
            if (REPO / path).is_symlink() and (REPO / path).is_dir():
                if path not in dirs:
                    dirs.add(path)
                    found.append(f"{path}: a symlink to a directory; remove it and link each file")
                return True
        return False

    for source in sorted(sources):
        link = Path(".claude/skills", *source.parts[2:])
        target = os.path.relpath(source, link.parent)
        if under_dir_link(link):
            continue
        actual = os.readlink(REPO / link) if (REPO / link).is_symlink() else None
        if actual != target:
            found.append(f"{link}: must be a symlink to {target}, not {actual or 'missing or a copy'}")
        elif link not in links:
            found.append(f"{link}: ignored by Git, so it would never be committed")
    for link in sorted(links):
        source = Path(".agents/skills", *link.parts[2:])
        if not under_dir_link(link) and source not in sources:
            found.append(f"{link}: nothing listed at {source} for it to point at")
    return sources, found


class SkillLinkTests(unittest.TestCase):
    def test_repository(self):
        sources, found = problems()
        self.assertTrue(sources, "No skill files listed under .agents/skills")
        self.assertEqual(found, [], HOW + "\n".join(found))


if __name__ == "__main__":
    unittest.main()
