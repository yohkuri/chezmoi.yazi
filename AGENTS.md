# Repository rules

These are the canonical instructions for AI agents in this repository. Claude
Code reads them through `CLAUDE.md`; other agents read this file directly. Keep
rules here instead of copying them into agent-specific files. The tracked
`.claude/` files only assist Claude Code: `settings.json` asks before the
common merge commands and pushes that name `main`, which other spellings can
bypass, and formats Lua files that `Write` or `Edit` touches; `rules/` and
`skills/` point it at the skills under `.agents/skills/`. The rules in this
file apply regardless.

## Language

All public repository content must be written in English, including documentation,
code comments, user-facing messages, commit messages, issues, pull request titles
and descriptions, review comments, and release notes. Non-English strings are
allowed only when required as test data, such as Unicode filename fixtures.
Keep emoji out of the repository's Markdown files, except at the head of
each point in the README's opening list. Private conversation with the user
may use their preferred language.

## GitHub Flow

- Use GitHub Flow: create a short-lived topic branch from `main`, make changes,
  open a pull request targeting `main`, validate and review it, then merge it.
- Never commit directly to `main` or push changes directly to `main`.
  `.githooks/pre-commit` refuses the commit, and `.githooks/pre-push` the push
  to this repository's GitHub remote; `CONTRIBUTING.md` says how to install
  them.
- Name topic branches `<type>/<short-subject>`, where `<type>` is a commit
  type that `@commitlint/config-conventional` accepts (`.commitlintrc.yml`
  extends it), unless the user specifies a different name. Dependabot's
  `dependabot/...` branches keep their own names.
- Every change must go through a pull request before it reaches `main`.
- Merge pull requests exclusively with **rebase and merge**. Do not use merge
  commits or squash merges.
- Complete the required checks and resolve review feedback before merging.
- Repository workflow rules do not authorize publishing: do not stage, commit,
  push, create a pull request, or merge without the user's authorization.
- Preserve unrelated work. Never reset, stash, overwrite, or delete it to make
  the working tree clean.
- For an empty repository, arrange initialization and branch protection with
  the user; do not silently bypass the prohibition on commits to `main`.

## Commit messages

- Follow Conventional Commits.
- Do not use emojis or Gitmoji in the subject, body, or footers.
- Start the subject with a lowercase letter, even when its first word is a
  proper noun such as `GitHub` or `API`: commitlint refuses `GitHub support`
  and accepts `add GitHub support`. Later in the subject, proper nouns keep
  their capitalization.
- Keep the complete header within 72 display columns and prefer subjects of
  at most 50 display columns. East Asian wide/fullwidth characters count as
  two columns; other characters count as one.

## Implementation and validation

- Keep plugin code, pure unit tests, and in-Yazi probes in Lua. Use Python
  standard-library code for runtime orchestration and fixture management.
- Manage Python through uv, never pip. Keep `uv.lock` current and use
  `uv run --locked`. Neovim is not a development or test dependency.
- Use `mise.toml` only to pin Lua, uv, and the LuaLS, StyLua, and ShellCheck
  that `test/check.py` runs; CI installs them from it. Do not define tasks or
  require mise to develop or test. Lua must match the tested Yazi embedded
  version, currently Lua 5.5.1 for Yazi 26.9.1.
- Keep test entry points directly executable, such as `test/manual.py`. Their
  shebang invokes uv with the locked environment. Document short commands
  run from the repository root; do not require wrapper command chains.
- Run `test/check.py` for Markdown, LuaLS, StyLua, ShellCheck, pure Lua
  tests, and Python syntax and harness unit tests.
  Install development dependencies with `npm ci --ignore-scripts` and
  `npm run setup:types` first. `CONTRIBUTING.md` lists the other tools, such
  as Node.js.
- Validate commit messages with `npm run lint:commits -- BASE HEAD`, or
  `npm run lint:commits -- --file PATH` before a commit exists.
  Commit messages must use ASCII English; this makes character lengths
  equal display columns and rejects emojis in bodies and footers too.
- Run the isolated runtime suite for changes affecting Yazi integration or
  the runtime harness:
  `test/runtime.py`.
  Use its optional `--git-plugin PATH`
  argument when validating git.yazi coexistence.
- Unit tests do not establish real rendering, fetcher, or shared-state behavior.
  State precisely which checks ran and which platforms remain unverified.
- Before changing the plugin's root Lua other than a comment, read
  `.agents/skills/implement-chezmoi-yazi/SKILL.md`.
- Before changing the test harness, validating a change, or reporting what
  was validated, read `.agents/skills/verify-chezmoi-yazi/SKILL.md`. Skills
  live under `.agents/skills/`; `test/test_skills.py` says how Claude Code
  reaches them.
- Use isolated temporary source, destination, config, state, and cache paths,
  and a private tmux socket. Never modify the user's dotfiles or Yazi setup as
  a test side effect. Preview scoped chezmoi changes before scoped apply.
- Clean up only test-owned temporary resources. Preserve failure diagnostics
  with `KEEP_FIXTURE=1` when needed.
- Keep the user docs (the README and the `docs/` pages other than
  `design.md` and `validation.md`), `CONTRIBUTING.md` instructions, design
  notes, validation evidence, and CI aligned with implementation changes.
  Record measured evidence without presenting unexecuted checks as passed.
