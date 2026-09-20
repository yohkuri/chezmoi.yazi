# Repository rules

## Language

All public repository content must be written in English, including documentation,
code comments, user-facing messages, commit messages, issues, pull request titles
and descriptions, review comments, and release notes. Non-English strings are
allowed only when required as test data, such as Unicode filename fixtures.
Private conversation with the user may use their preferred language.

## GitHub Flow

- Use GitHub Flow: create a short-lived topic branch from `main`, make changes,
  open a pull request targeting `main`, validate and review it, then merge it.
- Never commit directly to `main` or push changes directly to `main`.
- Use the `codex/` prefix for agent-created topic branches unless the user
  specifies a different branch name.
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
- Start the subject with a lowercase letter; proper nouns such as `GitHub` and
  `API` may retain their capitalization.
- Keep the complete header within 72 display columns and prefer subjects of
  at most 50 display columns. East Asian wide/fullwidth characters count as
  two columns; other characters count as one.

## Implementation and validation

- Keep plugin code, pure unit tests, and in-Yazi probes in Lua. Use Python
  standard-library code for runtime orchestration and fixture management.
- Manage Python through uv, never pip. Keep `uv.lock` current and use
  `uv run --locked`. Neovim is not a development or test dependency.
- Use `mise.toml` only to pin Lua and uv versions; do not define tasks or
  require mise to develop or test. Lua must match the tested Yazi embedded
  version, currently Lua 5.5.1 for Yazi 26.9.1.
- Keep test entry points directly executable, such as `test/manual.py`. Their
  shebang invokes uv with the locked environment. Document short commands
  run from the repository root; do not require wrapper command chains.
- Run `test/check.py` for Markdown, LuaLS, StyLua, pure Lua tests, and
  Python syntax and harness unit tests.
  Install development dependencies with `npm ci --ignore-scripts` and
  `npm run setup:types` first; see README for external tool versions.
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
- Use isolated temporary source, destination, config, state, and cache paths,
  and a private tmux socket. Never modify the user's dotfiles or Yazi setup as
  a test side effect. Preview scoped chezmoi changes before scoped apply.
- Clean up only test-owned temporary resources. Preserve failure diagnostics
  with `KEEP_FIXTURE=1` when needed.
- Keep README instructions, design notes, validation evidence, and CI aligned
  with implementation changes. Record measured evidence without presenting
  unexecuted checks as passed.
