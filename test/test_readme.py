"""Unit tests for how test/readme.py reads the README's setup."""
import unittest

import readme
from support import REPO, read

FILES = ["init.lua", "yazi.toml", "keymap.toml"]
INIT = "```lua\n-- ~/.config/yazi/init.lua\nrequire(\"chezmoi\"):setup()\n```\n"
YAZI = "```toml\n# ~/.config/yazi/yazi.toml\n[[plugin.prepend_fetchers]]\nurl = \"*\"\nrun = \"chezmoi\"\n```\n"
KEYMAP = "```toml\n# ~/.config/yazi/keymap.toml\n[[mgr.prepend_keymap]]\non = \"q\"\nrun = \"quit\"\n```\n"
THEME = "```toml\n# ~/.config/yazi/theme.toml\n[flavor]\ndark = \"catppuccin-mocha\"\n```\n"


def section(*blocks, after=""):
    return "# chezmoi.yazi\n\n## Quick start\n\n" + "\nProse.\n\n".join(blocks) + after


def blocks(*parts, after=""):
    return readme.setup_blocks(section(*parts, after=after), "## Quick start", FILES)


def readme_text(quick, theme):
    return section(*quick, after="\n## Theme and flavor\n\n" + "\n".join(theme))


class SetupBlockTests(unittest.TestCase):
    def test_keeps_each_block_as_it_stands(self):
        found = blocks(INIT, YAZI, KEYMAP)
        self.assertEqual(found["init.lua"], '-- ~/.config/yazi/init.lua\nrequire("chezmoi"):setup()\n')

    def test_skips_a_block_that_names_no_file(self):
        found = blocks("```toml\n[chezmoi]\nmanaged_sign = \"M\"\n```\n", INIT, YAZI, KEYMAP)
        self.assertEqual(sorted(found), sorted(FILES))

    def test_skips_a_block_named_for_another_file(self):
        other = "```toml\n# ~/.config/yazi/flavors/catppuccin-mocha.yazi/flavor.toml\n[mgr]\n```\n"
        self.assertEqual(sorted(blocks(other, INIT, YAZI, KEYMAP)), sorted(FILES))

    def test_refuses_a_missing_block(self):
        with self.assertRaisesRegex(ValueError, "no `keymap.toml` block"):
            blocks(INIT, YAZI)

    def test_a_heading_ends_the_section(self):
        with self.assertRaisesRegex(ValueError, "no `keymap.toml` block"):
            blocks(INIT, YAZI, after="\n## Next\n\n" + KEYMAP)

    def test_a_subheading_does_not(self):
        self.assertIn("keymap.toml", blocks(INIT, YAZI, "### Keys\n\n" + KEYMAP))

    def test_refuses_a_second_block_for_one_file(self):
        with self.assertRaisesRegex(ValueError, "a second `init.lua` block"):
            blocks(INIT, YAZI, KEYMAP, INIT)

    def test_refuses_a_toml_block_that_does_not_parse(self):
        with self.assertRaisesRegex(ValueError, "`yazi.toml` is not TOML"):
            blocks(INIT, YAZI.replace('"chezmoi"', '"chezmoi'), KEYMAP)

    def test_refuses_a_readme_without_the_section(self):
        with self.assertRaisesRegex(ValueError, "no `## Quick start` heading"):
            readme.setup_blocks("# chezmoi.yazi\n", "## Quick start", FILES)


class PictureTests(unittest.TestCase):
    def test_reads_the_readme_itself(self):
        found = readme.picture_blocks(read(REPO / "README.md"))
        self.assertEqual(sorted(found), sorted(FILES + ["theme.toml"]))
        self.assertIn('require("chezmoi"):setup()', found["init.lua"])
        self.assertTrue(found["yazi.toml"].endswith(readme.HIDDEN))
        self.assertTrue(readme.flavors(found["theme.toml"]))

    def test_shows_hidden_files(self):
        found = readme.picture_blocks(readme_text([INIT, YAZI, KEYMAP], [THEME]))
        self.assertEqual(found["yazi.toml"], YAZI[len("```toml\n"):-len("```\n")] + "\n[mgr]\nshow_hidden = true\n")

    def test_refuses_a_yazi_toml_that_already_has_mgr(self):
        yazi = YAZI.replace("[[plugin", "[mgr]\nratio = [1, 4, 3]\n\n[[plugin")
        with self.assertRaisesRegex(ValueError, "with `show_hidden` added is not TOML"):
            readme.picture_blocks(readme_text([INIT, yazi, KEYMAP], [THEME]))

    def test_reads_the_flavors_in_either_slot(self):
        theme = '[flavor]\ndark = "catppuccin-mocha"\nlight = "catppuccin-latte"\n'
        self.assertEqual(readme.flavors(theme), {"catppuccin-mocha", "catppuccin-latte"})
        self.assertEqual(readme.flavors('[chezmoi]\nmanaged = { fg = "blue" }\n'), set())


if __name__ == "__main__":
    unittest.main()
