"""Human UI acceptance, with file and state checks kept independent."""
import json
from support import NAMES


def step(*instructions, prep=(), files=None, absent=(), records=None, signs=None, no_action=None, special=None, epoch=None):
    closing = "If the UI is clear and readable, press P once; otherwise use W, then f."
    text = "\n".join(f"{i}. {line}" for i, line in enumerate([*instructions, closing], 1))
    return dict(instruction=text, prep=list(prep), files=files or {}, absent=list(absent),
                records=records or {}, signs=signs or {}, no_action=no_action, special=special, epoch=epoch)


def case(key, title, *steps, setup=(), optional=None):
    return dict(key=key, title=title, steps=list(steps), setup=list(setup), optional=optional)


CLEAN = {"membership": "managed", "xy": "  "}
CASES = [
    case("names", "Status, names and readability",
         step(
              'Inspect "clean" (C), "local" (CMM), "source" (C M), "remove-me" (C D), "unmanaged" and "ignored" (blank), and ".config" and ".exact" (*). Check that these states are visually distinct. W/d shows the sign legend; q then Enter returns.',
              f'Find {", ".join(json.dumps(name, ensure_ascii=False) for name in NAMES[4:])}. Use j/k and Space to check alignment and readability under the cursor, away from it and when selected. Check the status bar too.',
              "Press Escape until the selection is cleared. File contents, membership and status values are checked automatically when you press P.",
              absent=["script-ran"],
              records={"clean": CLEAN, "local": {"xy": "MM"}, "source": {"xy": " M"},
                       "unmanaged": {"membership": "unmanaged"}, "ignored": {"membership": "unmanaged"},
                       "remove-me": {"xy": " D"}, "link": CLEAN,
                       ".config": {"summary": "changed"}, ".exact": {"summary": "changed"},
                       **{name: CLEAN for name in NAMES[4:]}},
         ),
         step(
              "Press W, then h to hide the guide. Narrow and enlarge the terminal; check that the status columns and status bar remain readable and the file list is not corrupted.",
              "Press W, then h again to restore the guide. Check that instructions wrap and the controls remain accessible. Use W/d if full instructions do not fit.",
         ),
    ),
    case("errors", "Warnings, error signs and recovery",
         step(
              'The fixture has broken the template for "bad". Press R and read the template-error warning. Check that it is clear that a query failed, rather than a file operation being requested.',
              'Find "bad" (C!!) and "clean" (C). Check that the failure signs are visible and distinguishable from the clean display.',
              prep=[("remove", "source/bad"), ("write", "source/bad.tmpl", "{{ .missing.field }}\n")],
              records={"bad": {"failed": True}, "clean": CLEAN},
         ),
         step(
              'The fixture has repaired "bad" and broken a template below ".config". Press R and read the template-error warning.',
              'Move the cursor away from ".config". Check that its * and partial-result underline are visible and distinguishable. The repair of "bad" is checked automatically.',
              prep=[("write", "source/bad.tmpl", "original\n"), ("write", "source/dot_config/broken.tmpl", "{{ .missing.field }}\n")],
              records={".config": {"partial": True, "summary": "changed"}},
         ),
         step(
              "The fixture is set to fail chezmoi managed. Press R and read the membership-query warning.",
              "Check that ! replaces the managed sign and that directory errors are visible. Check that the warning and signs communicate a query failure, rather than unmanaged files.",
              prep=[("write", "state/instrument/control", "fail-managed")],
              records={"clean": {"membership": "error"}},
         ),
         step(
              "The fixture has repaired both queries and templates. Press R and inspect the recovered display.",
              'Check that "bad" and "clean" show C, "local" shows CMM, and ".config" keeps * without the partial-result underline. The old failure display should no longer be present.',
              prep=[("remove", "state/instrument/control"), ("write", "source/bad.tmpl", "original\n"),
                    ("remove", "source/dot_config/broken.tmpl")],
              records={"bad": CLEAN, "clean": CLEAN, "local": {"xy": "MM"}, ".config": {"partial": False}},
         ),
    ),
    case("theme", "Theme, wide signs and colors",
         step(
              'Find "local" and inspect the default CMM signs before changing the theme. Move the cursor away from it and check that the signs and status bar are readable.',
              records={"local": {"xy": "MM"}},
         ),
         step(
              "The fixture has installed a test flavor and theme. Press Y to reload the theme without running a chezmoi command.",
              'Move the cursor away from "local". Check that the managed sign is the wide 界, modified marks are lowercase m, and modified text is orange. Check that columns still line up and the status bar remains readable.',
              prep=[("theme", "custom")], signs={"managed": "界", "modified": "m"}, epoch="same",
         ),
         step(
              "The fixture has restored the base theme. Press Y to reload it.",
              'Check that "local" has the default CMM signs again and that the restored colors and status bar remain readable.',
              prep=[("theme", "base")], signs={"managed": "C"}, epoch="same",
         ),
    ),
    case("add", "Add, Re-add, template and encryption",
         step(
              'Move to "unmanaged" and press a to run chezmoi add --recursive=true. This single-file Add should go directly to command output without an approval prompt.',
              "Read the effect, target, Running (argv), output and exit code. Check that you can identify what ran, then press Enter and check that you return to usable Yazi. File results are checked automatically.",
              files={"source/unmanaged": "other\n", "dest/unmanaged": "other\n"},
         ),
         step(
              'The fixture has edited "unmanaged" in the destination. Move to it, press C to open the action menu, then r for chezmoi re-add --recursive=true. Check that the menu choice and effect are clear.',
              "Read the target, argv and command result, then press Enter. Check that you return to Yazi; the source update is verified automatically.",
              prep=[("write", "dest/unmanaged", "changed by destination\n")],
              files={"source/unmanaged": "changed by destination\n"},
         ),
         step(
              'The fixture has reset "unmanaged" to an unmanaged file. Move to it and press t for chezmoi add --recursive=true --template.',
              "Check that the execution screen identifies Add with --template and the correct target. Read the result and press Enter; template creation is checked automatically.",
              prep=[("remove", "source/unmanaged"), ("write", "dest/unmanaged", "other\n")],
              special="template-added",
         ),
         step(
              "The fixture has changed the template's destination. With \"unmanaged\" under the cursor, press r for chezmoi re-add --recursive=true.",
              "Read the effect text explaining that templates are skipped, the argv and command result. Press Enter and check that returning to Yazi is clear; preservation of the template is checked automatically.",
              prep=[("write", "dest/unmanaged", "new destination\n")],
              files={"source/unmanaged.tmpl": "other\n"},
         ),
         step(
              'The fixture has reset "unmanaged" again and supplied a disposable age key. Move to "unmanaged" and press z for chezmoi add --recursive=true --encrypt.',
              "Check that --encrypt, the target and result are clear on the execution screen, then press Enter. Encryption and decryption are checked automatically; do not inspect encrypted bytes yourself.",
              prep=[("remove", "source/unmanaged.tmpl"), ("write", "dest/unmanaged", "other\n")],
              files={"dest/unmanaged": "other\n"}, special="encrypted-added",
         ),
         setup=[("age",)],
    ),
    case("forget", "Forget confirmation and cancellation",
         step(
              'Move to "unmanaged", which this fixture already manages, and press f for chezmoi forget.',
              "Read the confirmation. Check that it clearly identifies the target and says source entries are removed while destination files are kept. Press n and check that cancellation returns to Yazi without a command screen.",
              files={"source/unmanaged": "other\n", "dest/unmanaged": "other\n"},
         ),
         step(
              "Press f again. Read each plugin confirmation page and approve with y. At the native chezmoi prompt, read the target and answer y.",
              "Read the command result and press Enter. Check that the two confirmation stages and return to Yazi are understandable. Source removal and destination retention are checked automatically.",
              absent=["source/unmanaged"], files={"dest/unmanaged": "other\n"},
         ),
         setup=[("match", "unmanaged")],
    ),
    case("destroy", "Destroy confirmation and execution",
         step(
              'Move to "clean" and press x for chezmoi destroy --recursive=true. Read the confirmation and check that it clearly warns about deleting both source and destination entries and names the correct target.',
              "Approve every plugin page with y, then read and approve the native chezmoi prompt. Read the result and press Enter; check that you return to usable Yazi. Deletion is checked automatically.",
              absent=["source/clean", "dest/clean"],
         ),
    ),
    case("apply", "Diff, Apply preview and approval",
         step(
              'Move to ".config" and press d for a recursive chezmoi diff. Read the effect, target, argv and diff; check that the changes are readable and that no Apply approval is requested.',
              "Press Enter and check that you return to Yazi. The automatic check verifies that viewing the diff did not execute the pending script.",
              absent=["script-ran"],
         ),
         step(
              'Move to "source" and press p for scoped Apply. Read the chezmoi diff, check that the target and proposed changes are clear, then press Enter.',
              "At the plugin confirmation, check that this is a request to apply those changes. Press n; check that cancellation returns to Yazi without an Apply execution screen. Unchanged files are checked automatically.",
              files={"dest/source": "original\n"}, absent=["script-ran"],
         ),
         step(
              'Move to ".config" and press p. Read the full scoped diff, including the pending script, then press Enter.',
              "Read the target, directory scope and effect on the Apply confirmation. Approve with y, read the execution result and press Enter. Check that the preview, approval and execution stages are clearly separated; file changes and script execution are checked automatically.",
              files={"dest/.config/new": "new\n", "script-ran": "", "dest/source": "original\n"},
         ),
    ),
    case("edit", "Edit, Edit and Apply, and interruption",
         step(
              'Move to "source" and press e for chezmoi edit --apply=false --watch=false. Check the effect, target and argv before entering the fixture editor.',
              "Type edited by fixture and press Enter. Read the result and press Enter again. Check that you return to Yazi without a diff or Apply approval; source-only editing is checked automatically.",
              files={"source/source": "edited by fixture\n", "dest/source": "original\n"},
         ),
         step(
              'With "source" under the cursor, press E for Edit and Apply. In the fixture editor, type cancelled edit and press Enter.',
              "Read the edit result and press Enter to see the diff. Read it and press Enter, then press n at the Apply confirmation. Check that the stage order and cancellation are clear; the source edit and unchanged destination are checked automatically.",
              files={"source/source": "cancelled edit\n", "dest/source": "original\n"},
         ),
         step(
              "Press E again. In the fixture editor, type accepted edit and press Enter. Read the edit result and press Enter to see the diff.",
              "Read the diff and press Enter, then approve Apply with y. Read the result and press Enter. Check that you can identify each command and when the destination is about to change; matching source and destination are checked automatically.",
              files={"source/source": "accepted edit\n", "dest/source": "accepted edit\n"},
         ),
         step(
              'The fixture is ready with accepted edit in the source entry and destination file. Move to "source", press E and press Ctrl-C at the fixture editor input.',
              "Read the failure result and press Enter. Check that no diff or Apply stage appears, the interruption is understandable, and j/k still work in Yazi. Unchanged files are checked automatically.",
              prep=[("write", "source/source", "accepted edit\n"), ("write", "dest/source", "accepted edit\n")],
              files={"source/source": "accepted edit\n", "dest/source": "accepted edit\n"},
         ),
         setup=[("editor", "manual")],
    ),
    case("rejections", "Rejected actions and safety messages",
         step(
              'Select "clean" and "unmanaged" with Space, then press e for Edit. Read the Not managed warning; check that it identifies the unsuitable target and that no editor or command screen opens.',
              "Keep the selection until this step is recorded. The automatic check verifies that Edit did not run.",
              files={"dest/clean": "original\n", "dest/unmanaged": "other\n"}, no_action="edit",
         ),
         step(
              'Press Escape until the selection is cleared. Move to ".config" and press e for Edit.',
              "Check that the warning asks you to select files inside the directory, rather than opening an editor. Check that the reason and next action are understandable.",
              no_action="edit",
         ),
         step(
              'Move to ".exact" and press D for chezmoi destroy --recursive=false.',
              "Read the rejection. Check that it explains why a non-recursive directory Destroy is unsafe, and that no approval or native command screen appears. Child preservation is checked automatically.",
              files={"dest/.local/share/chezmoi/exact_dot_exact/keep": "same\n", "dest/.exact/keep": "same\n"},
              no_action="destroy",
         ),
         step(
              'Press 5 to move to ".local" and press x for recursive Destroy. Read the source-directory protection warning. Press D and check that non-recursive Destroy is also rejected before approval.',
              'Enter ".local/share", move to "chezmoi" and press x. Read the warning for the source directory itself. Check that each refusal names the target and explains the reason, then press h twice to return. Source-state preservation is checked automatically.',
              files={"dest/.local/share/chezmoi/dot_bashrc": "unrelated\n", "dest/.local/share/chezmoi/dot_local/bin/tool": "tool\n", "dest/.local/bin/tool": "tool\n"},
              no_action="destroy",
         ),
         setup=[("nested-source",)],
    ),
    case("visual", "Multiple targets, direct action and menu",
         step(
              'Press 1, then v and j twice to highlight "range-a", "range-b" and "range-c". Press a for Add.',
              "Read the confirmation. Check that its effect, count of three targets and all three paths are understandable. Approve every page with y, read the command result and press Enter. Added files are checked automatically.",
              files={f"source/range-{c}": f"range {c}\n" for c in "abc"},
         ),
         step(
              'Clear the selection with Escape. Enter ".config", select "outside" with Space and press h to return. Press 2, then v and j twice to highlight "menu-a", "menu-b" and "menu-c".',
              'Press C, then a for Add. Read the confirmation and check that all four targets, including ".config/outside", can be identified even though one is in another directory. Approve every page with y, read the result and press Enter; all four additions are checked automatically.',
              files={**{f"source/menu-{c}": f"menu {c}\n" for c in "abc"}, "source/dot_config/outside": "outside\n"},
         ),
         setup=[("ranges",)],
    ),
    case("confirmation", "Confirmation pages and terminal resizing",
         step(
              "Press 4 to select six long, Unicode, control-character and deep-path targets. Press x for Destroy.",
              "Read every confirmation page. Check that all paths are escaped, readable and reachable. Press y between pages, then n on the final page; check that cancellation returns to Yazi without command output. Target preservation is checked automatically.",
              special="long-preserved",
         ),
         step(
              "At a wide terminal size, press x for the same selection. Stay on page 1 and resize the terminal narrower.",
              "Press y and check that Pane resized clearly explains the restart at page 1. Press n to cancel, then restore a comfortable size; all targets are checked automatically.",
              special="long-preserved",
         ),
         step(
              "Press W, then h to hide the guide. Resize the terminal to 40 columns by 12 rows or smaller, then press x.",
              "Check that the message asks you to enlarge the pane instead of showing an unusable confirmation. Enlarge the terminal and restore the guide with W/h; target preservation is checked automatically. The limit is a pane below 32 columns or 8 rows.",
              special="long-preserved",
         ),
         setup=[("long",)],
    ),
    case("git", "git.yazi coexistence",
         step(
              'Find "local" and check that git G appears before chezmoi CMM. Inspect other untracked rows as well.',
              "Use j/k and Space to inspect both plugins under the cursor, away from it and when selected. Check that the signs remain readable and distinct, then press Escape to clear the selection.",
              records={"local": {"xy": "MM"}},
         ),
         optional="git",
    ),
]
