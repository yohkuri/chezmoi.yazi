#!/usr/bin/env bash
# Every file under .agents/skills needs a relative symlink at the same path
# under .claude/skills, which is where Claude Code looks; a missing one is
# silent at both ends, as the skill is simply never offered. Links are per file
# because `ya pkg add` refuses a symlink to a directory and then installs
# nothing. Untracked files count too, so a new skill is checked before it is
# committed; CI has none.
set -euo pipefail
cd "$(dirname "$0")/.."

rc=0
list() {
  git ls-files -z --cached --others --exclude-standard -- "$1"
}

# A directory symlink hides the per-file links below it, so report it once and
# skip the files it covers.
# macOS ships bash 3.2, which has no associative arrays.
seen=$'\n'
dirlink() {
  local d=$1
  while [ "$d" != .claude/skills ] && [ "$d" != . ]; do
    if [ -L "$d" ] && [ -d "$d" ]; then
      if [[ $seen != *$'\n'"$d"$'\n'* ]]; then
        seen+=$d$'\n'
        echo "$d: a symlink to a directory, which \`ya pkg add\` refuses."
        echo "  rm $d, then link each file under it."
        rc=1
      fi
      return 0
    fi
    d=$(dirname "$d")
  done
  return 1
}

while IFS= read -r -d '' f; do
  l=.claude/skills/${f#.agents/skills/}
  up=$(printf '%s' "$l" | sed 's|[^/]||g; s|/|../|g')
  dirlink "$(dirname "$l")" && continue
  if [ ! -L "$l" ] && [ ! -e "$l" ]; then
    echo "$l: missing. Claude Code will not see $f."
    echo "  mkdir -p '$(dirname "$l")' && ln -s '$up$f' '$l'"
    rc=1
  elif [ ! -L "$l" ]; then
    echo "$l: not a symlink, so it goes stale when $f changes."
    echo "  ln -sf '$up$f' '$l'"
    rc=1
  elif [ "$(readlink "$l")" != "$up$f" ]; then
    echo "$l: points at '$(readlink "$l")', not '$up$f'."
    echo "  ln -sf '$up$f' '$l'"
    rc=1
  fi
done < <(list .agents/skills)

while IFS= read -r -d '' l; do
  dirlink "$l" && continue
  f=.agents/skills/${l#.claude/skills/}
  [ -n "$(list "$f" 2>/dev/null | tr -d '\0')" ] || {
    echo "$l: nothing at $f for it to point at."
    rc=1
  }
done < <(list .claude/skills)

exit $rc
