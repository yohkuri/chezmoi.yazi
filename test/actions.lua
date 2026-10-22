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
local function facts(source, entries, source_dirs)
	return {
		destination = "/d",
		source = source or "/d/source",
		managed = entries or managed,
		editable = entries or editable,
		source_dirs = source_dirs or {},
	}
end
local function plan(args, files, source_dirs)
	return actions.prepare(assert(actions.parse(args)), files, facts(nil, nil, source_dirs))
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
local replaced_dir, source_dirs = file("/d/dir"), { ["/d/dir"] = true }
check(
	plan({ "destroy", recursive = false }, { replaced_dir }, source_dirs) == nil,
	"reject nonrecursive destroy when only the source is a directory"
)
check(
	plan({ "destroy", recursive = false }, { file("/d/a"), replaced_dir }, source_dirs) == nil,
	"source directory rejects the entire selection"
)
check(
	plan({ "destroy" }, { replaced_dir }, source_dirs) ~= nil,
	"recursive destroy still accepts a replaced source directory"
)
check(plan({ "add" }, { file("/d/source/a") }) == nil, "reject source tree")
-- managed never lists the destination root.
for _, name in ipairs { "re-add", "diff", "apply" } do
	check(plan({ name }, { file("/d", true) }), name .. " may target the destination root")
	check(plan({ name, recursive = false }, { file("/d", true) }) == nil, name .. " targets the root only recursively")
end
check(
	actions.prepare(assert(actions.parse { "apply" }), { file("/d", true) }, facts(nil, {})) == nil,
	"no managed entry, no root"
)
check(plan({ "forget" }, { file("/d", true) }) == nil, "forget cannot target the destination root")
local nested_source = "/d/.local/share/chezmoi"
local nested_managed = { ["/d/a"] = true, ["/d/.local"] = true, ["/d/.local/bin"] = true, ["/d/.locality"] = true }
for _, path in ipairs { "/d", "/d/.local", "/d/.local/share", "/d/.local/bin/.." } do
	for _, recursive in ipairs { true, false } do
		local p, err = actions.prepare(
			assert(actions.parse { "destroy", recursive = recursive }),
			{ file("/d/a"), file(path, true) },
			facts(nested_source, nested_managed)
		)
		check(p == nil and err:find("contains the source directory", 1, true), "source ancestor rejects entire destroy")
	end
end
for _, name in ipairs { "add", "diff", "apply", "forget" } do
	check(
		actions.prepare(assert(actions.parse { name }), { file("/d/.local", true) }, facts(nested_source, nested_managed)),
		"source ancestor restriction applies only to destroy"
	)
end
for _, path in ipairs { "/d/.local/bin", "/d/.locality" } do
	check(
		actions.prepare(assert(actions.parse { "destroy" }), { file(path, true) }, facts(nested_source, nested_managed)),
		"destroy allows sibling directories and similar prefixes"
	)
end
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
p = assert(plan({ "add" }, {
	file("/d/tree", true),
	file("/d/tree-sibling", true),
	file("/d/tree/child"),
	file("/d/tree\nname", true),
	file("/d/tree\nname/child"),
}))
check(
	#p.targets == 3 and p.targets[1].path == "/d/tree" and p.targets[3].path == "/d/tree-sibling",
	"recursive reduction preserves sibling prefixes and newline directory boundaries"
)
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
check(args[2] == "--apply=false" and args[3] == "--watch=false", "edit disables native auto-apply and watch")
local plain_edit = actions.args(assert(plan({ "edit" }, { file("/d/a") })), {})
check(table.concat(args, "\0") == table.concat(plain_edit, "\0"), "plain edit has the same safe edit stage")
local diff, apply = actions.args(p, {}, "diff"), actions.args(p, {}, "apply")
diff[1] = "apply"
check(table.concat(diff, "\0") == table.concat(apply, "\0"), "preview and apply use identical scope/options")
check(not table.concat(apply):find("no%-tty"), "no query flags in interactive action")
local forced = false
local both = { file("/d/a"), file("/d/dir", true) }
for _, case in ipairs {
	{ { "add" }, both },
	{ { "add", template = true, encrypt = true }, both },
	{ { "add", recursive = false }, both },
	{ { "re-add" }, both },
	{ { "re-add", recursive = false }, both },
	{ { "diff" }, both },
	{ { "diff", recursive = false }, both },
	{ { "apply" }, both },
	{ { "apply", recursive = false }, both },
	{ { "forget" }, both },
	{ { "destroy" }, both },
	{ { "destroy", recursive = false }, { file("/d/a") } },
	{ { "edit" }, { file("/d/a") } },
	{ { "edit", apply = true }, { file("/d/a") } },
} do
	local planned = assert(plan(case[1], case[2]))
	for _, stage in ipairs { planned.action.name, "edit", "diff", "apply" } do
		for _, arg in ipairs(actions.args(planned, {}, stage)) do
			if not forced and arg:find("^%-%-force") then
				forced = planned.action.name .. " plan, " .. stage .. " stage: " .. arg
			end
		end
	end
end
check(not forced, "no action passes --force: " .. tostring(forced))
local discovery = [[execute-template {{ .chezmoi.destDir }}{{ "\x00" }}{{ .chezmoi.sourceDir }}]]
local queries = {
	managed = "managed --include=all --exclude=none --path-style=absolute --nul-path-separator",
	editable = "managed --include=files,symlinks,dirs --exclude=externals --path-style=absolute --nul-path-separator",
	source_dirs = "managed --include=dirs --exclude=externals --path-style=absolute --nul-path-separator",
}
-- Each query lists only its own name, so facts cannot swap their results unnoticed.
local function chezmoi(failing)
	local calls = {}
	return function(args)
		local call = table.concat(args, " ")
		calls[#calls + 1] = call
		if failing and call:find(failing, 1, true) then
			return nil, "exit"
		end
		if call == discovery then
			return "/d\0/d/source"
		end
		for name, query in pairs(queries) do
			if call == query then
				return "/d/" .. name .. "\0"
			end
		end
		return nil, "exit"
	end,
		calls
end
for _, case in ipairs {
	{ { "add" }, { "managed" } },
	{ { "re-add" }, { "managed" } },
	{ { "diff" }, { "managed" } },
	{ { "apply" }, { "managed" } },
	{ { "edit", apply = true }, { "managed", "editable" } },
	{ { "forget" }, { "managed", "editable" } },
	{ { "destroy" }, { "managed", "editable" } },
	{ { "destroy", recursive = false }, { "managed", "editable", "source_dirs" } },
} do
	local run, calls = chezmoi()
	local fresh = assert(actions.facts(assert(actions.parse(case[1])), run))
	local expected = { discovery }
	for _, query in ipairs(case[2]) do
		expected[#expected + 1] = queries[query]
	end
	check(
		table.concat(calls, "\n") == table.concat(expected, "\n"),
		"fresh queries for " .. case[1][1] .. ": " .. table.concat(calls, " | ")
	)
	check(fresh.destination == "/d" and fresh.source == "/d/source", "facts directories")
	local queried = {}
	for _, query in ipairs(case[2]) do
		queried[query] = true
	end
	for _, query in ipairs { "managed", "editable", "source_dirs" } do
		check(
			queried[query] and fresh[query] and fresh[query]["/d/" .. query] or not queried[query] and fresh[query] == nil,
			query .. " holds its own query's result, only when queried"
		)
	end
end
for failing, message in pairs {
	["execute-template"] = "Cannot resolve chezmoi context",
	[queries.managed] = "Cannot acquire managed targets",
	[queries.editable] = "Cannot acquire source entries",
	[queries.source_dirs] = "Cannot acquire source directories",
} do
	local run = chezmoi(failing)
	local fresh, err = actions.facts(assert(actions.parse { "destroy", recursive = false }), run)
	check(fresh == nil and err:find(message, 1, true) and err:find("No action was run", 1, true), message)
end
check(not actions.display("a\n\27b"):find("[%c]"), "escape display controls")
check(actions.summary(p, "apply"):find("Source %-> destination"), "describe direction")
print("PASS " .. n .. " action policy assertions")
