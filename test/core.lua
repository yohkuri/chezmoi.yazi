local core = dofile("core.lua")
local n = 0
local function equal(actual, expected, label)
	n = n + 1
	assert(
		actual == expected,
		(label or ("assertion " .. n)) .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual)
	)
end
equal(core.path("/a/./b/../c/"), "/a/c")
equal(core.path("sftp://host/x"), nil)
equal(core.path("/a\0b"), nil)
equal(core.path("/back\\slash"), "/back\\slash")
equal(core.inside("/ab", "/a"), false)
equal(core.inside("/a/b", "/a"), true)
equal(core.inside("/a", "/"), true)
local index = assert(core.managed("/d/a\0/d/space name\0/d/new\nline\0", "/d"))
equal(index["/d/new\nline"], true)
for _, bad in ipairs { "/d/a", "\0", "/d/a\0\0", "/d/a\0/d/a\0", "/elsewhere\0" } do
	equal(core.managed(bad, "/d"), nil, "reject invalid managed stream")
end
local coverage = { ["/d/a"] = true, ["/d/space name"] = true }
equal(core.status(" M /d/space name\n", coverage)["/d/space name"], " M")
for _, bad in ipairs {
	" M /d/a",
	"MM /d/a\n\n",
	"ZZ /d/a\n",
	" M /d/other\n",
	" M /d/a\n M /d/a\n",
	"  /d/a\n",
} do
	equal(core.status(bad, coverage), nil, "reject invalid status stream")
end
equal(core.status("DA /d/new\nline\n", {}, "/d/new\nline")["/d/new\nline"], "DA")
equal(core.status("DA /d/new\nline\n M /d/a\n", {}, "/d/new\nline"), nil)
equal(#core.chunks({ "aaaa", "bbbb", "cc" }, 9), 2)

local opts = { directory_summary = true, argument_bytes = 8192, max_retries = 8 }
local managed = { "/d/clean", "/d/dir", "/d/dir/new", "/d/dir/other", "/d/local" }
local statuses = { ["/d/dir/new"] = " A", ["/d/dir/other"] = " D", ["/d/local"] = "MM" }
local broken, calls, empty_queries, recursive_queries, max_argument_bytes = {}, 0, 0, 0, 0
local function run(args)
	if args[1] == "execute-template" then
		return "/d"
	end
	if args[1] == "managed" then
		return table.concat(managed, "\0") .. "\0"
	end
	calls = calls + 1
	local targets, recursive, after = {}, false, false
	for _, arg in ipairs(args) do
		if after then
			targets[#targets + 1] = arg
		end
		if arg == "--" then
			after = true
		end
		if arg == "--recursive=true" then
			recursive = true
			recursive_queries = recursive_queries + 1
		end
	end
	if #targets == 0 then
		empty_queries = empty_queries + 1
	end
	local bytes = 0
	for _, target in ipairs(targets) do
		bytes = bytes + #target + 1
	end
	max_argument_bytes = math.max(max_argument_bytes, bytes)
	local covered = {}
	for _, path in ipairs(managed) do
		for _, root in ipairs(targets) do
			if path == root or recursive and core.inside(path, root) then
				covered[path] = true
			end
		end
	end
	local lines = {}
	for _, path in ipairs(managed) do
		if covered[path] then
			if broken[path] then
				return nil, "exit"
			end
			if statuses[path] then
				lines[#lines + 1] = statuses[path] .. " " .. path .. "\n"
			end
		end
	end
	return table.concat(lines)
end
local files = {
	{ path = "/d/clean" },
	{ path = "/d/local" },
	{ path = "/d/unmanaged" },
	{ path = "/d/dir", dir = true },
}
local r = core.collect(files, opts, run)
equal(r.records["/d/clean"].xy, "  ")
equal(r.records["/d/local"].xy, "MM")
equal(r.records["/d/unmanaged"].membership, "unmanaged")
equal(r.records["/d/dir"].xy, "  ")
equal(r.records["/d/dir"].summary, "changed")
equal(r.error, nil)
equal(calls, 1, "one scoped batch")
statuses["/d/dir/new"], statuses["/d/dir/other"], statuses["/d/local"] = nil, nil, nil
r = core.collect(files, opts, run)
equal(r.records["/d/local"].xy, "  ", "clear resolved own change")
equal(r.records["/d/dir"].summary, "clean", "clear resolved summary")
broken["/d/dir/new"] = true
r = core.collect(files, opts, run)
equal(r.records["/d/clean"].xy, "  ", "recover independent file")
equal(r.records["/d/dir"].xy, "  ", "preserve own status after child error")
equal(r.records["/d/dir"].summary, "error")
equal(r.error, "exit")
statuses["/d/dir/other"] = " D"
r = core.collect(files, opts, run)
equal(r.records["/d/dir"].summary, "changed")
equal(r.records["/d/dir"].partial, true)
opts.directory_summary = false
r = core.collect(files, opts, run)
equal(r.records["/d/dir"].summary, nil)
equal(r.records["/d/dir"].xy, "  ")
equal(r.error, nil, "disabled summary avoids unrelated broken child")
opts.directory_summary, broken = true, {}
managed[#managed + 1] = "/d/dir/new\nline"
statuses["/d/dir/new\nline"] = " A"
recursive_queries = 0
r = core.collect(files, opts, run)
equal(r.records["/d/dir"].summary, "changed")
equal(r.error, nil)
equal(recursive_queries, 0, "exceptional descendant forbids recursive line parsing")
equal(empty_queries, 0)
local before = calls
core.collect({ { path = "/d/unmanaged" } }, opts, run)
equal(calls, before, "do not query status without managed targets")
opts.max_retries = 2
for _, path in ipairs(managed) do
	broken[path] = true
end
before = calls
core.collect(files, opts, run)
equal(calls - before <= 4, true, "bounded failure subdivision")
r = core.collect(files, opts, function() return nil, "spawn" end)
equal(r.records["/d/clean"].membership, "error")
equal(r.error, "spawn")
table.remove(managed) -- Remove the exceptional path to force a recursive batch.
for i = 1, 100 do
	local path = "/d/dir/long-name-" .. i
	managed[#managed + 1], broken[path] = path, true
end
opts.argument_bytes, max_argument_bytes = 256, 0
before = calls
core.collect(files, opts, run)
equal(max_argument_bytes <= 256, true, "recovery respects argument byte budget")
equal(calls - before <= 3, true, "expanded recovery still respects total retry budget")
print("PASS " .. n .. " core assertions")
