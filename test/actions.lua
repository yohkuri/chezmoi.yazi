package.loaded[".core"] = dofile("core.lua")
local actions = dofile("actions.lua")
local n = 0
local function check(value, label)
	n = n + 1
	assert(value, label)
end
local function file(path, dir) return { path = path, local_path = true, exists = true, dir = dir or false } end
local managed = { ["/d/a"] = true, ["/d/dir"] = true, ["/d/dir/b"] = true, ["/d/script"] = true }
local editable = { ["/d/a"] = true, ["/d/dir"] = true, ["/d/dir/b"] = true }
local function plan(args, files)
	return actions.prepare(assert(actions.parse(args)), files, "/d", "/d/source", managed, editable)
end

for _, args in ipairs {
	{ "remove" },
	{ "apply", force = true },
	{ "add", "extra" },
	{ "forget", recursive = false },
	{ "edit", recursive = true },
	{ "menu", encrypt = true },
	{ "add", template = "yes" },
	{ "refresh", unexpected = true },
	{ "unknown" },
	{ "diff", apply = true },
} do
	check(actions.parse(args) == nil, "reject unsupported command/options")
end
check(actions.parse({}).name == "refresh", "keep default refresh")
check(actions.parse({ "add", recursive = "false" }).recursive == false, "Yazi string boolean")
check(actions.parse({ "add", template = true, encrypt = true }).encrypt, "combined add options")
check(plan({ "apply" }, {}) == nil, "empty never means all")
check(plan({ "apply" }, { file("/d/a"), file("/d/unmanaged") }) == nil, "mixed selection is all-or-nothing preflight")
check(plan({ "edit" }, { file("/d/dir", true) }) == nil, "do not expand directories for edit")
check(
	plan({ "destroy", recursive = false }, { file("/d/dir", true) }) == nil,
	"reject unsafe nonrecursive directory destroy"
)
check(
	plan({ "destroy", recursive = false }, { file("/d/a"), file("/d/dir", true) }) == nil,
	"unsafe directory rejects the entire selection"
)
check(plan({ "add" }, { file("/d/source/a") }) == nil, "reject source tree")
check(plan({ "add" }, { file("/elsewhere") }) == nil, "reject destination escape")
check(plan({ "add" }, { file("/d/../elsewhere") }) == nil, "normalize before validation")
check(plan({ "add" }, { { path = "sftp://host/a" } }) == nil, "reject nonlocal URL")
check(plan({ "forget" }, { file("/d/script") }) == nil, "managed does not mean editable")
check(plan({ "add" }, { { path = "/d/a", local_path = true, exists = false } }) == nil, "reject disappeared selection")
check(
	plan({ "add" }, { { path = "/d/fifo", local_path = true, exists = true, special = true } }) == nil,
	"reject special file"
)
local p = assert(plan({ "apply" }, { file("/d/dir/b"), file("/d/dir", true), file("/d/a"), file("/d/a") }))
check(#p.targets == 2 and p.broad, "recursive parent covers child; deduplicate")
p = assert(plan({ "diff", recursive = false }, { file("/d/dir/b"), file("/d/dir", true) }))
check(#p.targets == 2, "nonrecursive preserves child")
check(not actions.confirm_before(assert(plan({ "add" }, { file("/d/new") }))), "single add has no plugin confirmation")
check(actions.confirm_before(assert(plan({ "add" }, { file("/d/new", true) }))), "directory add confirms")
check(actions.confirm_before(assert(plan({ "forget" }, { file("/d/a") }))), "forget always confirms")
check(actions.confirm_before(assert(plan({ "destroy" }, { file("/d/a") }))), "destroy always confirms")
p = assert(plan({ "destroy", recursive = false }, { file("/d/a") }))
check(actions.args(p, {}, "destroy")[2] == "--recursive=false", "allow nonrecursive destroy of a file")
check(not actions.confirm_before(assert(plan({ "edit" }, { file("/d/a") }))), "edit opens directly")
local names = {
	"space name",
	"日本語",
	'quote"name',
	"back\\slash",
	"new\nline",
	"carriage\rreturn",
	"-dash",
	"$(touch sentinel)",
}
for _, name in ipairs(names) do
	p = assert(plan({ "add", template = true, encrypt = true }, { file("/d/" .. name) }))
	local args = actions.args(p, { config = "/cfg with spaces", source = "/src", persistent_state = "/state" })
	check(args[#args] == "/d/" .. name and args[#args - 1] == "--", "paths remain literal arguments")
	check(args[2] == "/cfg with spaces" and args[6] == "/state", "context stays separate")
end
p = assert(plan({ "edit", apply = true }, { file("/d/a") }))
local args = actions.args(p, {}, "edit")
check(#args == 3 and args[1] == "edit", "edit never invokes native --apply")
local diff, apply = actions.args(p, {}, "diff"), actions.args(p, {}, "apply")
diff[1] = "apply"
check(table.concat(diff, "\0") == table.concat(apply, "\0"), "preview and apply use identical scope/options")
check(not table.concat(apply):find("no%-tty"), "no query flags in interactive action")
check(not actions.display("a\n\27b"):find("[%c]"), "escape display controls")
check(actions.summary(p, "apply"):find("Source %-> destination"), "describe direction")
print("PASS " .. n .. " action policy assertions")
