#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
# With no commits yet, validate a prospective message using --file PATH.
if [ "${1:-}" = '--file' ] && [ "$#" -eq 2 ]; then
  lua scripts/check-ascii.lua < "$2"
  commitlint --config .commitlintrc.yml < "$2"
elif [ "$#" -eq 2 ]; then
  head=$(git rev-parse --verify "$2^{commit}")
  if [ "$1" = "--all" ]; then
    commits=$(git rev-list "$head")
  else
    base=$(git rev-parse --verify "$1^{commit}")
    commits=$(git rev-list "$base..$head")
  fi
  test -n "$commits" || { echo 'No commits in range.'; exit 0; }
  for commit in $commits; do
    git show -s --format=%B "$commit" | lua scripts/check-ascii.lua
    git show -s --format=%B "$commit" | commitlint --config .commitlintrc.yml
  done
else
  echo 'Usage: npm run lint:commits -- BASE HEAD | --all HEAD | --file MESSAGE_FILE' >&2
  exit 2
fi
