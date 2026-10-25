---
name: implement-chezmoi-yazi
description: >-
  Where the reasons behind the plugin's root Lua are written, and how to find
  the tests that match what a change touches. Read before changing the
  plugin's root Lua other than a comment; not for choosing or reporting
  tests, which `verify-chezmoi-yazi` covers.
---

# Changing the plugin

## Read the reason first

The invariants and their reasons are in `docs/design.md`, including the
decisions D3 and D4; in `CONTRIBUTING.md`'s How the code is laid out; in
the README's sections that promise behavior to users, such as Commands and
Evaluation and limits; and in comments in the code. Read the parts that
cover what you change. This skill does not restate them: every earlier draft
that did got them wrong somewhere.

## Find the tests that match the change

The suites match some of the plugin's messages, arguments and flags
literally: the pure suites, the Python harness, and the guide text under
`test/`. Before changing a string, an argument or a flag, search `test/` for
it. A match may be a copy that changes with it, or a check that the old value
must stay, such as the query flags that `support.check_call` requires; decide
which from the design and the README before changing the test. Strings that no
test matches are not covered, so check them against the design instead.

Many of these matches run only in the Yazi-driven suites, so a green
`test/check.py` does not show that a change kept them;
`verify-chezmoi-yazi` says which suites a change needs.
