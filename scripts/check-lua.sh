#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
test -f .dev/types/yazi.lua || {
  echo 'Run npm run setup:types first.' >&2
  exit 1
}
logs=$(mktemp -d "${TMPDIR:-/tmp}/chezmoi-yazi-luals.XXXXXX")
trap 'rm -rf "$logs"' EXIT HUP INT TERM
lua-language-server --check . --checklevel Warning --logpath "$logs/plugin" --metapath "$logs/meta-plugin"
lua-language-server --check test --configpath "$PWD/test/.luarc.json" \
  --checklevel Warning --logpath "$logs/test" --metapath "$logs/meta-test"
