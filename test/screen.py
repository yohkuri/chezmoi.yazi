"""Pure helpers for reading chezmoi linemode values and boxes from a tmux capture."""
import re
import unicodedata

BAR = "│"
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
DECORATIONS = str.maketrans("", "", "")


def plain(text):
    return ANSI.sub("", text)


def current_rows(capture):
    """Return current-pane rows without ANSI control sequences."""
    rows = []
    for line in plain(capture).splitlines():
        panes = line.split(BAR, 2)
        if len(panes) == 3:
            rows.append(panes[1].translate(DECORATIONS))
    return rows


def _name_pattern(name):
    return re.compile(r"^\s*\S+\s+" + re.escape(name) + r"(?=\s|$)")


def row(capture, name, *, ansi=False):
    """Return the one current-pane row whose primary filename is name."""
    pattern = _name_pattern(name)
    matches = []
    for raw_line in capture.splitlines():
        raw_panes = raw_line.split(BAR, 2)
        if len(raw_panes) != 3:
            continue
        raw = raw_panes[1]
        visible = plain(raw).translate(DECORATIONS)
        if pattern.search(visible):
            matches.append(raw if ansi else visible)
    if not matches:
        return None
    if len(matches) != 1:
        raise AssertionError(f"Multiple current-pane rows matched {name!r}")
    return matches[0]


def status(capture, name):
    """Return the four default MXYD characters for name, or None."""
    return linemode(capture, name, 4)


def linemode(capture, name, length):
    """Return the final linemode characters, excluding Yazi's row edge."""
    value = row(capture, name, ansi=True)
    if value is None:
        return None
    value = plain(value)
    hovered = value.endswith("")
    value = value.translate(DECORATIONS)
    if not hovered:
        value = value[:-1]
    return value[-length:] if len(value) >= length else None


def cell_width(text):
    """Measure terminal cells for the fixture's text after removing SGR."""
    return sum(_cells(character) for character in plain(text))


def _cells(character):
    if unicodedata.combining(character) or unicodedata.category(character) == "Cf":
        return 0
    return 2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1


def box_rows(capture, title):
    """Return the stripped rows inside the box titled title, or None until
    every row has both side borders and the bottom border is drawn."""
    lines = plain(capture).splitlines()
    top = next((i for i, line in enumerate(lines) if "╭" in line and title in line), None)
    if top is None:
        return None
    left = cell_width(lines[top].split("╭")[0])
    width = cell_width(lines[top].split("╭")[1].split("╮")[0])
    rows = []
    for line in lines[top + 1:]:
        column, text, edges, inside = 0, "", "", False
        for character in line:
            size = _cells(character)
            if size == 0:
                # A combining mark belongs to the cell before it.
                text += character if inside else ""
                continue
            inside = left < column <= left + width
            if inside:
                text += character
            elif column in (left, left + width + 1):
                edges += character
            column += size
        if edges == "╰╯":
            return rows
        # A capture can catch a redraw half done, or a notification over the
        # box; reading on would take in text that is not the box's.
        if edges != BAR * 2:
            return None
        rows.append(text.strip())
    return None
