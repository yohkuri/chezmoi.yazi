"""Pure helpers for reading chezmoi linemode values from a tmux capture."""
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
    width = 0
    for character in plain(text):
        if unicodedata.combining(character) or unicodedata.category(character) == "Cf":
            continue
        width += 2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
    return width
