"""Pure helpers for reading chezmoi linemode values and boxes from a tmux capture."""
import re
import unicodedata

BAR = "│"
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
DECORATIONS = str.maketrans("", "", "")


def plain(text):
    return ANSI.sub("", text)


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
    top = next(_tops(lines, title), None)
    return None if top is None else _box(lines, *top)


def box_texts(capture, title):
    """Return the text of every whole box titled title, its rows joined and
    its whitespace dropped: a wrap can drop the space where it breaks, so
    compare with compact text."""
    lines = plain(capture).splitlines()
    boxes = (_box(lines, *top) for top in _tops(lines, title))
    return [compact("".join(rows)) for rows in boxes if rows is not None]


def compact(text):
    return "".join(text.split())


SGR = re.compile(r"\x1b\[([0-9;:]*)m")


def background(capture, text):
    """Return the SGR background in effect where text first shows in an ansi
    capture, or None for the default. capture-pane -e carries attributes from
    one line to the next, so read every change before text."""
    found = None
    for match in SGR.finditer(capture[:capture.index(text)]):
        params = (match.group(1) or "0").split(";")
        i = 0
        while i < len(params):
            code = params[i] or "0"
            if code in ("38", "48", "58"):
                # Extended colors take two (5;N) or four (2;R;G;B) more fields.
                width = 3 if params[i + 1:i + 2] == ["5"] else 5
                if code == "48":
                    found = ";".join(params[i:i + width])
                i += width
                continue
            if code in ("0", "49"):
                found = None
            elif code.isdigit() and (40 <= int(code) <= 47 or 100 <= int(code) <= 107):
                found = code
            i += 1
    return found


def _tops(lines, title):
    """Yield the line and the indexes of both top corners of each box whose top
    border, not the rest of its line, holds title."""
    for i, line in enumerate(lines):
        corner = line.find("╭")
        while corner != -1:
            end = line.find("╮", corner)
            # Another corner before end means this box's right corner is hidden.
            if end != -1 and "╭" not in line[corner + 1:end] and title in line[corner:end]:
                yield i, corner, end
            corner = line.find("╭", corner + 1)


def _box(lines, top, corner, end):
    left = cell_width(lines[top][:corner])
    width = cell_width(lines[top][corner + 1:end])
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
