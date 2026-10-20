#!/bin/sh
# Claude Code PostToolUse hook from .claude/settings.json: format the Lua file
# that a Write or Edit touched with the StyLua version mise.toml pins, which CI
# installs too. Exit status 2 hands stderr back to the agent, so a missing tool,
# a version mismatch or a StyLua error is fixed in the same session instead of
# surfacing later in CI.
#
# The file is formatted only inside a checkout of this repository, which may be
# a worktree, and only where `stylua --check .` in test/check.py would look:
# not under a hidden path such as .github, and not in a path Git ignores.
set -u

fail() {
  printf 'format-lua-hook: %s\n' "$1" >&2
  exit 2
}

input=$(cat)
# Most edits are not Lua; let them through before requiring jq.
case "$input" in
*'.lua"'*) ;;
*) exit 0 ;;
esac
command -v jq >/dev/null 2>&1 || fail 'jq is not installed'
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty') ||
  fail 'jq could not read the hook input'
case "$file" in
*.lua) ;;
*) exit 0 ;;
esac
project=${CLAUDE_PROJECT_DIR:-}
[ -n "$project" ] && [ -f "$file" ] || exit 0
command -v git >/dev/null 2>&1 || fail 'git is not installed'

# CLAUDE_PROJECT_DIR stays at the main checkout while a session works in a
# worktree, so find the checkout from the file and accept it when it shares
# the project's repository. Git resolves symlinks such as /tmp on macOS.
dir=$(dirname -- "$file")
top=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null) || exit 0
prefix=$(git -C "$dir" rev-parse --show-prefix) || exit 0
common=$(git -C "$dir" rev-parse --path-format=absolute --git-common-dir) ||
  exit 0
ours=$(git -C "$project" rev-parse --path-format=absolute --git-common-dir \
  2>/dev/null) || exit 0
[ "$common" = "$ours" ] || exit 0

rel=$prefix$(basename -- "$file")
case "/$rel" in
*/.*) exit 0 ;;
esac
# 0 is ignored and 1 is not.
git -C "$top" check-ignore -q -- "$rel"
case $? in
0) exit 0 ;;
1) ;;
*) fail "git check-ignore failed for $file" ;;
esac

pins=$top/mise.toml
want=$(sed -n 's/^stylua[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$pins")
[ -n "$want" ] || fail "could not read the stylua version from $pins"
# mise's shims pick a version by the working directory, so run StyLua where
# the file's own mise.toml applies. A PATH set by `mise activate` does not
# follow it; the version check below catches what that leaves.
cd "$top" || fail "could not enter $top"
command -v stylua >/dev/null 2>&1 ||
  fail "StyLua is not installed; CI uses StyLua $want"
have=$(stylua --version) || fail 'stylua --version failed'
have=${have#stylua }
[ "$have" = "$want" ] ||
  fail "$file was not formatted: StyLua $have is installed, but CI uses $want.
Install StyLua $want, with \`mise install\` if you use mise, then run it on the
file."

out=$(stylua --config-path .stylua.toml -- "$rel" 2>&1) ||
  fail "StyLua could not format $file:
$out"
