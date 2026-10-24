-- Loads main.lua with stubs for the Yazi globals that setup and an entry's
-- notification paths touch; ya.sync runs each block on one shared state. rawset
-- keeps LuaLS from checking the stubs against Yazi's full types.
package.loaded[".core"] = dofile("core.lua")
package.loaded[".actions"] = dofile("actions.lua")
package.loaded[".process"] = dofile("process.lua")
package.loaded[".render"] = { theme = function() return {} end }
package.loaded[".interaction"] = dofile("interaction.lua")
local n = 0
local function equal(actual, expected, label)
	n = n + 1
	assert(actual == expected, label .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual))
end

local st, notices = {}, {}
rawset(_G, "ya", {
	target_family = function() return "unix" end,
	sync = function(f)
		return function(...) return f(st, ...) end
	end,
	notify = function(opt) notices[#notices + 1] = opt end,
	emit = function() end,
	time = function() return 0 end,
})
rawset(_G, "ui", { render = function() end })
rawset(_G, "ps", { sub = function() end })
rawset(_G, "Linemode", { children_add = function() return 1 end, children_remove = function() end })
rawset(_G, "cx", { active = { selected = {}, current = { files = {} } } })
local main = dofile("main.lua")

main.setup(st, {})
equal(st.opts.notify_timeout, 7, "default notify_timeout")
for _, value in ipairs { 0, -1, 0 / 0, math.huge, "2", 0.0001, 2e9 } do
	local ok, err = pcall(main.setup, {}, { notify_timeout = value })
	equal(not ok and tostring(err):find("Invalid chezmoi option: notify_timeout", 1, true) ~= nil, true, tostring(value))
end
for _, value in ipairs { 0.001, 1e9 } do
	equal(pcall(main.setup, {}, { notify_timeout = value }), true, tostring(value))
end

-- Each path sets the timeout from a different notify_timeout, so a path that
-- skips it keeps the previous value and fails.
for i, case in ipairs {
	{ args = { "bogus" }, content = "Unknown chezmoi command" },
	{ args = { "apply" }, content = "No target" },
	{ args = { "apply" }, content = "already running", busy = true },
} do
	main.setup(st, { notify_timeout = i / 2 })
	st.action_busy = case.busy
	local before = #notices
	main.entry(main, { args = case.args })
	equal(#notices, before + 1, case.content)
	equal(notices[#notices].content:find(case.content, 1, true) ~= nil, true, case.content)
	equal(notices[#notices].timeout, i / 2, case.content)
end
st.action_busy = false
main.setup(st, {})
equal(st.opts.notify_timeout, 7, "default notify_timeout after an entry")
print("PASS " .. n .. " main assertions")
