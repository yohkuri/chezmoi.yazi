# Contributing

Thanks for looking! Bug reports and pull requests are both very welcome.

This page is everything you need to start; you don't have to read anything
else first. (`AGENTS.md` holds the rules for AI agents working here. You can
skip it.) If your change alters what the plugin does, also read what
[Change the plugin](#change-the-plugin) points at. If you add or change a
test, read `.agents/skills/verify-chezmoi-yazi/SKILL.md` too.

## What you need

**Yazi 26.9.1 and chezmoi.** Older Yazi releases refuse to load the plugin,
and newer ones are untested. If you report something you saw on screen,
please mention your OS and the versions you ran (`yazi -V`,
`chezmoi --version`).

Lua, uv, lua-language-server, StyLua and ShellCheck are pinned in
`mise.toml`. If you use [mise], `mise trust` and `mise install` fetch them;
if you don't, install the same versions with your preferred installer.
`mise.toml` defines no tasks, and CI installs the same tools from it, so
with mise a local check runs the analyzers CI runs; `test/check.py` does not
compare their versions. Match StyLua's version exactly: another release can
format the same file differently, and CI would refuse what yours passed.

| For | What |
| --- | ---- |
| Markdown | Node.js 24 or newer |
| commit messages | Node.js 24 or newer, Git, and Lua from `mise.toml` |
| unit tests | Lua 5.5.1 from `mise.toml`, the version Yazi 26.9.1 embeds |
| the Python harness and its unit tests | uv from `mise.toml`, and Git; nothing installed with pip |
| Lua types, Lua formatting and shell scripts | lua-language-server, StyLua and ShellCheck from `mise.toml` |
| the Claude Code hook that formats Lua | jq, Git, and StyLua from `mise.toml` |
| `test/runtime.py` | Yazi with its `ya` command, chezmoi and tmux; Git with `--git-plugin` |
| `test/e2e.py` | Yazi, chezmoi and tmux; Git with `--git-plugin` |
| `test/manual_runtime.py` | Yazi, chezmoi, tmux and Git |
| `test/manual.py` | Yazi, chezmoi, Git and a real terminal; no tmux |
| `test/readme.py` | Yazi, chezmoi, a real terminal with a Nerd Font, and the flavor the README names installed with `ya pkg add`; no tmux |
| `test/benchmark.py` | chezmoi |

The pinned Lua matches the Yazi 26.9.1 build: its `lua55` feature and
locked `lua-src` 551.0.1 embed Lua 5.5.1. The separate Lua executable is for
unit tests; it does not replace Yazi's embedded runtime. uv selects Python
3.14 through `.python-version` and keeps `.venv` and `uv.lock`. The Python
harness uses only the standard library. The executable scripts under `test/`
start through uv with the locked environment, so there is no separate Python
setup step. Neovim is not needed.

None of these tools is a dependency of the plugin itself, and no personal
Yazi configuration is needed.

## Get the code

Fork the repository on GitHub, then clone your fork and point it back at
the original:

```sh
git clone https://github.com/<your-username>/chezmoi.yazi.git
cd chezmoi.yazi
git remote add -f upstream https://github.com/yohkuri/chezmoi.yazi.git
```

You'll push to `origin` (your fork) and pull from `upstream` to stay in
step with `main`. The `-f` fetches `upstream` straight away, so
`upstream/main` exists before anything below asks for it.

To try your checkout in your own Yazi, link it in as the plugin, then set
it up as the README's [Quick start](README.md#quick-start) says. If you
installed the plugin with `ya pkg add`, run `ya pkg delete yohkuri/chezmoi`
first. Run these from the clone's root; they find Yazi's configuration
directory as Yazi does, and refuse when something is already there:

```sh
plugin=${YAZI_CONFIG_HOME:-${XDG_CONFIG_HOME:-$HOME/.config}/yazi}/plugins/chezmoi.yazi
mkdir -p "${plugin%/*}"
test ! -e "$plugin" && ln -s "$PWD" "$plugin" || echo "$plugin is already there"
```

## Install the git hooks

Nothing installs them for you. Install them once per clone; these lines
also work from a linked worktree or a clone without `.git/hooks`, and `ln`
refuses to replace a hook that is already there:

```sh
common=$(git rev-parse --path-format=absolute --git-common-dir)
mkdir -p "$common/hooks"
ln -s "${common%/.git}/.githooks"/* "$common/hooks/"
```

- `.githooks/pre-commit` refuses a commit on `main`, in your fork too:
  there, as here, a change goes through a topic branch, and syncing `main`
  from `upstream` fast-forwards without a commit.
  `CHEZMOI_YAZI_COMMIT_ON_MAIN=1 git commit ...` commits on `main`
  deliberately.
- `.githooks/pre-push` refuses a push to `main` of this GitHub repository,
  and leaves your fork's `main` alone. Branch protection on GitHub refuses
  such a push anyway; the hook only catches it earlier.

Both print how to move the commits to a topic branch.

The links follow whatever the main worktree has checked out, so the hooks
stop running while it is at a commit without `.githooks/`. A
`core.hooksPath` setting replaces `.git/hooks`, so with one set, these hooks
run only if the hooks in that path pass control on to `.git/hooks`.
`test/test_githooks.py` checks which remotes and refs they refuse.

## Run the checks

From the repository root:

```sh
npm ci --ignore-scripts
npm run setup:types
test/check.py
```

`npm ci` installs the JavaScript tools locked in `package-lock.json`.
`npm run setup:types` downloads Yazi's type annotations into the ignored
`.dev/types`, at a fixed revision checked against a SHA-256.
`types/compat.lua` adds the runtime declarations they lack and the plugin's
theme extension.

`test/check.py` runs `npm run check`, which:

- lints Markdown with `.markdownlint-cli2.yaml`;
- checks the Lua with lua-language-server as Lua 5.5: the root and
  `scripts/` with `.luarc.json`, which loads `types/` and the downloaded
  annotations as libraries, and `test/`, including the in-Yazi probes, with
  `test/.luarc.json`;
- checks formatting with StyLua and `.stylua.toml`;
- runs ShellCheck on `.githooks/*` and `scripts/*.sh`;
- runs the pure Lua status and action suites, and a stubbed `main.lua`
  suite for setup options and notification timeouts;
- checks Python syntax and runs the harness unit tests, among them
  `test/test_skills.py`, which checks that every file under
  `.agents/skills/` has its symlink under `.claude/skills/`.

CI runs all of this on your pull request, and adds two things
`test/check.py` does not:

- the status and action suites under Lua 5.1 and 5.4, and `luac -p` under
  5.1, 5.4 and 5.5 over the `*.lua` files in the root, `test/` and
  `scripts/`. A Lua 5.5-only construct there passes locally and fails in
  CI, unless you install `lua5.1` and `lua5.4` and run the same commands
  from `.github/workflows/check.yml`;
- the E2E smoke scenario, `test/e2e.py --smoke`, on Ubuntu 24.04 with
  SHA-256-pinned Yazi and chezmoi release binaries.

CI also checks your commit messages; see [Commit messages](#commit-messages).

## Test in Yazi

The other suites run the real chezmoi, and all but `test/benchmark.py`
start a real Yazi. Run them from the repository root with the tools on
`PATH`; none of them invokes mise. Every fixture is isolated, with its own
source, destination, config, state and cache directories, and the suites
that use tmux give it a private socket. Nothing applies your dotfiles or
edits your Yazi configuration.

| Command | What it does |
| ------- | ------------ |
| `test/runtime.py` | Integration tests that read the plugin's state through an internal probe |
| `test/e2e.py` | Black-box tests that see only the terminal, the process and the files |
| `test/manual.py` | An interactive fixture with a guide, for a person to walk |
| `test/manual_runtime.py` | The guide's walk, with its keys pressed by a script |
| `test/readme.py` | The README's Quick start in your terminal, for the README's picture |
| `test/benchmark.py` | Timings of the chezmoi queries the plugin runs |
| `test/all.py` | `test/check.py`, `test/runtime.py`, `test/e2e.py` and `test/manual_runtime.py` at once |

Which of them your change needs, in short:

- every change: `test/check.py`;
- the plugin's Lua (the `*.lua` files in the root): also `test/runtime.py`,
  `test/e2e.py` and `test/manual_runtime.py`;
- the harness under `test/`: the suites the skill below names for the
  files you changed;
- docs, CI or tooling outside `test/` alone: nothing more.

`.agents/skills/verify-chezmoi-yazi/SKILL.md` maps each file under `test/`
to its suites, says when a `test/all.py` run is not enough on its own, and
holds the rules for writing a test: how a fixture stays isolated, what it
may clean up, and how to wait on the screen.

### `test/runtime.py`

```sh
test/runtime.py
```

It checks the rendered terminal output as well as the plugin's records.
Each case runs in a fresh fixture; `--case NAME` runs only that case,
repeated to select more, and `--help` lists the names.
`--git-plugin /absolute/path/to/git.yazi` checks that the plugin coexists
with a git.yazi checkout, and then the `status` case, which holds that
check, always runs. Set `KEEP_FIXTURE=1` to keep a fixture for debugging.

Like the E2E and guide suites, it opens its pane with `test/da1.py`
answering the device attributes query that Yazi sends through tmux. With
no terminal behind the private tmux, Yazi would otherwise wait five seconds
for the answer each time it hides for a command or quits.

### `test/e2e.py`

```sh
test/e2e.py
test/e2e.py --smoke
# Optional, using an existing git.yazi checkout:
test/e2e.py --git-plugin /absolute/path/to/git.yazi
```

It starts a fresh isolated Yazi for each scenario and checks the visible
terminal output, the process's exit and the fixture files. It runs the real
chezmoi binary directly, without the runtime suite's probe or command
wrapper. `--case NAME` runs one scenario, `--keep` keeps the fixtures, and
`--artifacts DIR` saves failure captures and logs.

### `test/manual.py`

```sh
test/manual.py
```

It starts Yazi directly in your terminal, with ordered English instructions
in a guide at the bottom. Its 12 cases focus on readable rendering, command
screens, confirmations, cancellation, warnings and the return to Yazi. File
and state correctness is checked automatically; refresh, navigation and
selection bookkeeping stay in the automated suites.

Press `P` once after each step to record a visual PASS, check the files and
state, and advance on success, or `S` to skip the step and advance. `W`
opens the other verdicts, retries and diagnostics; `q` saves the results
and offers cleanup. No second terminal, later shell commands or tmux are
needed. The [guided manual acceptance walk](test/MANUAL.md) covers the
controls and what each case checks.

`test/manual_runtime.py` presses the guide's keys in a private tmux. It
checks that the guide runs; it is not a person's walk, whatever verdicts it
records.

### `test/readme.py`

```sh
test/readme.py
```

The picture at the top of the README is a screenshot of it. It writes the
README's Quick start and the `theme.toml` block under Theme and flavor as
they stand into a scratch home, with hidden files shown, and links the
flavor from where `ya pkg add` put yours. In that home it builds dotfiles
that chezmoi reports in each state the picture shows, waits for the window
to reach the size it names and opens Yazi in your terminal. Quitting Yazi
removes the scratch home. Take the screenshot outside tmux, on the
flavor's background, `#1e1e2e` for Catppuccin Mocha, at a font size that
makes a column about 14 pixels wide, so the picture is about 1400 pixels
wide and stays sharp on a Retina display. Raise it for that window alone,
with Command-= in Ghostty, rather than in your configuration, and before
the window reaches the size: a font change takes columns away, and once
Yazi is open nothing checks the size again. Capture the window without its
shadow: on macOS, Command-Shift-4, then Space, then a click on the window
with Option held.

It is not in CI, and nothing compares the picture with what the setup
draws: retake it after a change moves what the picture shows.
`test/test_readme.py` checks only that the README's blocks still read.

### `test/all.py`

It runs its four suites at once, in about the guide's time alone, and
prints each suite's output whole as it ends. Run one at a time, with no
other guide run or walk meanwhile; its docstring says why. It runs neither
`test/benchmark.py` nor `--git-plugin`.

## Commit messages

[Conventional Commits], with the rules of
[`@commitlint/config-conventional`][config-conventional] that
`.commitlintrc.yml` extends, and a few of its own. The ones people trip on:

- The type is one of `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`,
  `refactor`, `revert`, `style` and `test`; `deps:` is refused.
- The header, the whole first line including `type:`, is **72 characters
  or fewer.** That limit is hard.
- **Plain ASCII English, in the whole message**, body and footers too.
  ASCII makes the header's length equal its display columns and rules out
  emoji, and also curly quotes and accented letters: `don't`, not `don’t`.
- Start the subject with a lowercase letter, even when its first word is a
  name: `add GitHub support`, not `GitHub support`. Later in the subject,
  names like `GitHub` or `API` keep their capitals.
- The subject does not end with a full stop.
- A blank line separates the body from the header, and lines in the body
  and footers are 100 characters or fewer.

Aim for 50 characters in the subject, the part after `type:`, or after
`type(scope)!:`, and its space, if it fits; going over is only a warning.
Check your commits before pushing:

```sh
npm run lint:commits -- upstream/main HEAD
# Before the first commit, check a prospective message instead:
npm run lint:commits -- --file /absolute/path/to/message.txt
```

In a clone of this repository rather than a fork, use `origin/main` in
place of `upstream/main`. It uses `.commitlintrc.yml` and
`scripts/check-ascii.lua`, the same checks
CI runs on the commits of a pull request and on pushed ranges, including
every commit on a newly created branch.

Everything here is written in English, commit messages included.

## Open a pull request

For anything bigger than a small fix, please open an issue first so we can
agree on the shape of it. Finding out that a finished change needs redoing
is no fun for anyone. For a typo or an obvious bug, just send the pull
request.

Nobody pushes to `main`, not even the maintainer. The server refuses it.
Everything goes through a pull request:

1. Bring your `main` up to date with `git fetch upstream`, then
   `git switch main && git merge --ff-only upstream/main`, and branch off
   it, commit, and push to your fork with `git push -u origin HEAD`. Name
   the branch `<type>/<short-subject>`, with a commit type such as `fix` or
   `docs`.
2. Open the pull request. Say which of the commands above you ran, and on
   which OS, Yazi and chezmoi.
3. To catch up with `main`, use `git fetch upstream` then
   `git rebase upstream/main`, and push with `git push --force-with-lease`,
   which refuses rather than drops a commit someone else pushed to your
   branch meanwhile. Please don't merge `main` into your branch, and don't
   use the pull request's Update branch button, which merges by default:
   the commit check refuses a merge commit's message.
4. Once the checks are green and the review is settled, the maintainer
   merges it with rebase and merge.

Your commits land on `main` exactly as you wrote them, which is why the
message rules above are checked rather than tidied up afterwards.

Dependabot opens one grouped pull request a month for the npm packages and
one for the workflows' actions, plus one for each security fix as it is
published (`.github/dependabot.yml`). It does not update `mise.toml`, the
type annotations' revision, the workflows' runner labels, or the
SHA-256-pinned Yazi and chezmoi downloads. Its commits go through the same
commit check.

## How the code is laid out

The layout follows [Yazi's plugin overview][plugin-overview]: `main.lua` is
the entry point, with `README.md` and `LICENSE` at the plugin root. `setup`
stores the configuration and render state in the synchronous plugin state;
`entry` and `fetch` do the asynchronous work. Every `ya.sync` block is
declared unconditionally at the top level. Messages between contexts carry
plain values and tables, never live file userdata or UI objects. The
leading `@since` annotation enforces the supported Yazi minimum. Raising
it moves the plugin to a newer Yazi: on the push to `main`,
`.github/workflows/tag.yml` tags the commit `main` stood at before as
`yazi-<old version>`, which the README tells users of the older Yazi to pin.
Land the changes the newer Yazi needs in the same pull request, and fixes
meant for the older Yazi in an earlier one: the tag names `main` before that
pull request, so no commit of its own reaches the older Yazi.

| Module | Responsibility |
| ------ | -------------- |
| `main.lua` | `setup`, `fetch` and `entry`, the synchronous state, the worker queue, and the linemode child. |
| `core.lua` | Pure parsing, query planning and reduction. chezmoi runs only through an injected `run`; no Yazi globals or filesystem I/O. |
| `actions.lua` | Command policy, preflight queries and argument construction, independent of Yazi's UI. |
| `interaction.lua` | Asynchronous UI, local file metadata, and staged execution of the actions a person asks for. |
| `process.lua` | Running chezmoi: background queries with a timeout, an output limit, cancellation and stderr discarded, built on the flags `M.client` adds; and `M.interactive`, which hands the terminal to a command with no timeout. |
| `render.lua` | The signs and styles from the theme, and the cells of a row. |

The user docs are the README and the `docs/` pages other than `design.md`
and `validation.md`, now `docs/commands.md` and `docs/configuration.md`.
`docs/design.md` records the accepted decisions and their reasons, and
`docs/validation.md` the evidence behind them and the platforms that remain
unverified.

The plugin and its unit suites, and the probes that run inside Yazi, are
Lua; process control, fixtures and the benchmark are Python. The public age
key in the fixture is example data for disposable tests only.

## Change the plugin

Before changing the plugin's Lua other than a comment, read
`.agents/skills/implement-chezmoi-yazi/SKILL.md`. It says where the
reasons behind the code are written, among them
[How the code is laid out](#how-the-code-is-laid-out), and how to tell a
test that should follow your change from one that guards against it.

A change that alters what the user docs, this page, `test/MANUAL.md`,
`docs/design.md` or CI describe updates them in the same pull request. A
change that alters what was validated adds a dated entry to
`docs/validation.md`: what ran, on which OS, Yazi and chezmoi, the counts
`test/check.py` printed, what failed first and why, and what stays
unverified.

## Using AI

A lot of this repository was written with AI agents. Many commits say so
with a `Co-Authored-By` trailer, though not every commit an agent helped
with carries one. It seems only fair to mention
that before saying anything about your tools.

So use whatever helps. The one thing we ask is that you have read what you
send, run it, and can talk it through. A change nobody can explain is hard
to review, whoever or whatever wrote it.

If you use Claude Code, it reads the tracked `.claude/settings.json`. After
its `Write` or `Edit` tool touches a Lua file, the settings run
`scripts/format-lua-hook.sh`. It formats the files that `test/check.py`
checks, in this checkout or one of its worktrees, and skips hidden and
Git-ignored paths. It needs jq, Git, and the StyLua version that
`mise.toml` pins. A missing tool, a different StyLua version, or a
formatting failure leaves the file unchanged and is reported back to the
agent. It runs StyLua from the file's checkout, so mise's shims pick the
version that checkout pins; a `PATH` set by `mise activate` does not follow
it, and the version check then refuses. `test/test_format_hook.py` checks
that it reads the version from `mise.toml` and how it calls StyLua. The
settings also ask before common merge commands and pushes that name `main`.

Other agents and editors do not run this hook, so `test/check.py` remains
the formatting check. Rules under `.claude/rules/` attach when Claude Code
reads a matching file and point it at the skills in `.agents/skills/`: for
the plugin's root Lua, `implement-chezmoi-yazi` and, before reporting a
change as validated, `verify-chezmoi-yazi`; for files under `test/`,
`verify-chezmoi-yazi`.

## License

By contributing, you agree your work is licensed under the MIT License,
as `LICENSE` says.

[Conventional Commits]: https://www.conventionalcommits.org/
[config-conventional]: https://github.com/conventional-changelog/commitlint/tree/master/%40commitlint/config-conventional
[mise]: https://mise.jdx.dev/
[plugin-overview]: https://yazi-rs.github.io/docs/plugins/overview/
