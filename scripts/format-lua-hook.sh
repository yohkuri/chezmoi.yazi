#!/bin/sh
# Claude Code PostToolUse hook from .claude/settings.json: format the Lua file
# that a Write or Edit touched. Paths outside the project and paths Git ignores
# (.dev/types, node_modules, .claude/worktrees) are left alone. Exit status 2
# hands stderr back to the agent, so a missing tool or a StyLua error is fixed
# in the same session instead of surfacing later in CI.
set -u

fail() {
  printf 'format-lua-hook: %s\n' "$1" >&2
  exit 2
}

file=$(jq -r '.tool_input.file_path // empty') || fail 'jq could not read the hook input'
case "$file" in
*.lua) ;;
*) exit 0 ;;
esac
root=${CLAUDE_PROJECT_DIR:-}
[ -n "$root" ] && [ -f "$file" ] || exit 0
case "$file" in
"${root%/}"/*) ;;
*) exit 0 ;;
esac

# 0 is ignored and 1 is not; anything else, such as a path that leaves the
# repository through `..`, is not ours to format.
git -C "$root" check-ignore -q -- "$file" 2>/dev/null
case $? in
1) ;;
*) exit 0 ;;
esac

out=$(stylua --config-path "${root%/}/.stylua.toml" -- "$file" 2>&1) ||
  fail "StyLua could not format $file:
$out"
