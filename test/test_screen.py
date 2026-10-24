"""Unit tests for terminal capture parsing used by the E2E suite."""
import unittest

import screen


class ScreenTests(unittest.TestCase):
    def capture(self, rows):
        return "\n".join(f" parent │{value}│ preview" for value in rows)

    def test_reads_exact_filename_and_status(self):
        capture = self.capture([
            "  source-old                 CMM  ",
            "  source                     C M  ",
        ])
        self.assertEqual(screen.status(capture, "source"), "C M ")
        self.assertEqual(screen.status(capture, "source-old"), "CMM ")

    def test_returns_none_for_missing_or_wrong_pane(self):
        capture = "  source CMM │  other C   │  source C D "
        self.assertIsNone(screen.status(capture, "source"))

    def test_preserves_blank_unmanaged_status(self):
        capture = self.capture(["  unmanaged                       "])
        self.assertEqual(screen.status(capture, "unmanaged"), "    ")

    def test_strips_ansi_and_hover_decorations(self):
        capture = self.capture([" \x1b[33m local                 CMM \x1b[0m"])
        self.assertEqual(screen.status(capture, "local"), "CMM ")
        self.assertIn("\x1b[33m", screen.row(capture, "local", ansi=True))

    def test_current_rows_require_three_panes(self):
        capture = "header\nleft│middle│right\nleft│incomplete"
        self.assertEqual(screen.current_rows(capture), ["middle"])

    def test_cell_width_handles_wide_and_combining_text(self):
        self.assertEqual(screen.cell_width("界m e\N{COMBINING ACUTE ACCENT}"), 5)

    def test_box_rows_require_whole_borders(self):
        box = ["top ╭ chezmoi destroy (1/2) ╮",
               "    │界ab                   │",
               "    │ Continue?             │",
               "    ╰───────────────────────╯ end"]
        self.assertEqual(screen.box_rows("\n".join(box), "chezmoi destroy"), ["界ab", "Continue?"])
        marked = [box[0], "    │界ab                  e\u0301│", *box[2:]]
        self.assertEqual(screen.box_rows("\x1b[31m" + "\n".join(marked), "chezmoi destroy")[0],
                         "界ab                  e\u0301")
        covered = [*box[:2], "    │ Cont╭ notice ──────────", box[3]]
        unfinished = [*box[:3], " NOR  status bar under the box"]
        for capture in [covered, unfinished, box[1:]]:
            self.assertIsNone(screen.box_rows("\n".join(capture), "chezmoi destroy"))

    def test_box_texts_join_wrapped_rows_of_every_whole_box(self):
        notices = ["  ╭ chezmoi──╮",
                   "  │Rejected: │",
                   "  │/dest/spac│",
                   "  │e name    │",
                   "  ╰──────────╯",
                   "  ╭ chezmoi──╮",
                   "  │Rejected: │",
                   "  │/dest/b   │",
                   "  ╰──────────╯",
                   "  ╭ chezmoi──╮",
                   "  │Covered   │"]
        texts = screen.box_texts("\n".join(notices), "chezmoi")
        self.assertEqual(texts, ["Rejected:/dest/spacename", "Rejected:/dest/b"])
        self.assertIn(screen.compact("Rejected: /dest/space name"), texts[0])

    def test_box_titles_come_from_the_top_border(self):
        # A pane left of a box can show the title; a box on the same line is
        # read from its own corner.
        lines = [" chezmoi.db ╭ other──╮ ╭ chezmoi─╮",
                 " cache      │Left    │ │Right    │",
                 " data       ╰────────╯ ╰─────────╯"]
        self.assertEqual(screen.box_texts("\n".join(lines), "chezmoi"), ["Right"])
        self.assertEqual(screen.box_rows("\n".join(lines), "other"), ["Left"])
        # A box whose right corner another box covers is not read through it.
        covered = [" ╭ other──╭ chezmoi─╮",
                   " │Left    │Right    │",
                   " ╰────────╰─────────╯"]
        self.assertEqual(screen.box_texts("\n".join(covered), "chezmoi"), ["Right"])
        self.assertIsNone(screen.box_rows("\n".join(covered), "other"))

if __name__ == "__main__":
    unittest.main()
