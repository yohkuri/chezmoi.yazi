-- Fixture setup prefixes python/backend/session/initial values.
local M = {}
-- The pinned type file omits constructor constants.
---@type any
local Layout = ui.Layout
local Root = rawget(_G, "Root")
local Tabs = rawget(_G, "Tabs")
local Backdrop = rawget(_G, "Backdrop")
local Header = rawget(_G, "Header")
local Tab = rawget(_G, "Tab")
local Status = rawget(_G, "Status")
local Modal = rawget(_G, "Modal")

local function summary(v)
	local r = v.result
	return "Files: " .. (r.files or "pending") .. " | State: " .. (r.diagnostic or "pending") .. " | Visual: " .. r.visual
end

function M:setup()
	self.view, self.hidden = initial, false
	local layout, build = Root.layout, Root.build
	local guide = { _id = "manual-guide" }
	function guide:new(area) return setmetatable({ _area = area }, { __index = self }) end
	function guide:reflow() return { self } end
	function guide:redraw()
		local v = M.view
		local title = v.finished and "Walk complete - q: results and finish"
			or string.format("%d/%d %s - step %d/%d", v.case, v.total, v.title, v.step, v.steps)
		local lines = self._area.h == 1 and { title .. " | W: controls" }
			or {
				title,
				"Do: " .. v.instruction,
				"Expect: " .. v.expect,
				"[W] Controls | " .. (M.busy and "Preparing/checking..." or summary(v)),
			}
		local text = ui.Text(lines):wrap(ui.Wrap.NO)
		text:area(self._area)
		return { text }
	end
	function Root:layout()
		if M.hidden then
			return layout(self)
		end
		self._chunks = Layout()
			:direction(Layout.VERTICAL)
			:constraints({
				ui.Constraint.Length(1),
				ui.Constraint.Length(Tabs.height()),
				ui.Constraint.Fill(1),
				ui.Constraint.Length(self._area.h < 20 and 1 or 4),
				ui.Constraint.Length(1),
			})
			:split(self._area)
	end
	function Root:build()
		if M.hidden then
			return build(self)
		end
		self._children = {
			Backdrop:new(self._area),
			Header:new(self._chunks[1], cx.active),
			Tabs:new(self._chunks[2]),
			Tab:new(self._chunks[3], cx.active),
			guide:new(self._chunks[4]),
			Status:new(self._chunks[5], cx.active),
			Modal:new(self._area),
		}
	end
end

local lock = ya.sync(function(st)
	if st.busy or st.action_pending or require("chezmoi").action_busy then
		return nil
	end
	st.busy = true
	ui.render()
	return st.view
end)
local release = ya.sync(function(st, value)
	if value then
		st.view = value
	end
	st.busy = false
	ui.render()
end)
local snapshot = ya.sync(function()
	local st = require("chezmoi")
	return {
		records = st.records,
		epoch = st.epoch,
		signs = st.theme.signs,
		cwd = tostring(cx.active.current.cwd),
		running = st.running or false,
		action_busy = st.action_busy or false,
	}
end)
local switch = ya.sync(function(_, v)
	for _ = 2, #cx.tabs do
		ya.emit("tab_switch", { 0 })
		ya.emit("close", {})
	end
	ya.emit("escape", { visual = true, select = true })
	require("chezmoi"):setup(v.opts)
	ya.emit("cd", { v.opts.destination })
	ya.emit("app:theme", {})
end)
local toggle = ya.sync(function(st)
	st.hidden = not st.hidden
	ui.render()
end)
local action = ya.sync(function(st, args)
	if st.busy or st.action_pending or require("chezmoi").action_busy then
		return false
	end
	st.action_pending = true
	ya.emit("plugin", args)
	return true
end)
local action_finished = ya.sync(function(st, release_pending)
	if release_pending then
		st.action_pending = false
	end
	return not require("chezmoi").action_busy
end)
local navigate = ya.sync(function(st, key)
	local dest = st.view.opts.destination
	if st.busy or st.action_pending then
		return
	end
	if key == "H" then
		ya.emit("tab_switch", { 0 })
	elseif key == "G" then
		ya.emit("tab_create", { dest .. "/.config" })
	elseif key == "N" then
		ya.emit("cd", { dest .. "/.config" })
	elseif key == "B" then
		ya.emit("cd", { dest })
	else
		local target = ({
			["1"] = "/range-a",
			["2"] = "/menu-a",
			["3"] = "/.config/outside",
			["5"] = "/.local",
			["6"] = "/source",
			["7"] = "/unmanaged",
			["8"] = "/clean",
			["9"] = "/.config",
			["0"] = "/.exact",
		})[key]
		if target then
			ya.emit("reveal", { dest .. target })
		end
	end
end)

local long_targets = ya.sync(function(st)
	if st.busy or st.action_pending then
		return nil
	end
	st.busy = true
	return { root = st.view.opts.destination, names = st.view.targets }
end)
local hovered = ya.sync(function() return cx.active.current.hovered and tostring(cx.active.current.hovered.url) end)
local function select_long()
	local targets = long_targets()
	if not targets then
		return
	end
	local ok, err = pcall(function()
		ya.emit("escape", { visual = true, select = true })
		for _, name in ipairs(targets.names) do
			local path = targets.root .. "/" .. name
			ya.emit("reveal", { path })
			local deadline = ya.time() + 5
			while hovered() ~= path do
				if ya.time() > deadline then
					error("Could not reveal confirmation target")
				end
				ya.sleep(0.02)
			end
			ya.emit("toggle", { state = "on" })
			ya.sleep(0.02)
		end
	end)
	release()
	if not ok then
		ya.notify { title = "Manual guide", content = tostring(err), timeout = 8, level = "error" }
	end
end

local function request(v, operation, extra)
	local payload = extra or {}
	payload.token, payload.snapshot = v.token, snapshot()
	if operation == "pass" or operation == "fail" or operation == "check" then
		local deadline = ya.time() + 8
		while payload.snapshot.running and ya.time() < deadline do
			ya.sleep(0.05)
			payload.snapshot = snapshot()
		end
	end
	local output, err =
		require("chezmoi.process").run(python, { backend, session, operation, ya.json_encode(payload) }, 30, 4194304)
	if not output then
		error("Guide backend failed: " .. tostring(err))
	end
	return assert(ya.json_decode(output))
end

local function details()
	local permit = ui.hide()
	local status = Command(python)
		:arg({ backend, session, "details" })
		:stdin(Command.INHERIT)
		:stdout(Command.INHERIT)
		:stderr(Command.INHERIT)
		:status()
	permit:drop()
	if not status or not status.success then
		error("Could not show guide details")
	end
end

local function controls(v, exit)
	local keys = exit
			and {
				{ "d", "Results and diagnostics" },
				{ "k", "Save, retain fixtures and exit" },
				{ "c", "Save and exit; clean fixtures unless any attempt failed" },
			}
		or {
			{ "n", "Next step (requires visual verdict or skip)" },
			{ "p", "Record visual PASS and check files/state" },
			{ "f", "Record visual FAIL" },
			{ "s", "Skip current step" },
			{ "r", "Restart case with fresh fixture" },
			{ "j", "Jump to case" },
			{ "d", "Full instructions, results, files and logs" },
			{ "h", "Hide/show guide (normal layout)" },
			{ "q", "Results and finish" },
		}
	local cands = {}
	for _, item in ipairs(keys) do
		cands[#cands + 1] = { on = item[1], desc = item[2] }
	end
	local choice = ya.which { cands = cands }
	if not choice then
		return v
	end
	local key = keys[choice][1]
	if key == "d" then
		v = request(v, "check")
		details()
	elseif key == "h" then
		toggle()
	elseif key == "q" then
		return controls(v, true)
	elseif key == "k" or key == "c" then
		v = request(v, "finish", { keep = key == "k" })
		ya.emit("quit", {})
	elseif key == "j" then
		local value, event = ya.input { title = "Case number (W/d lists all cases):", pos = { "center", w = 50 } }
		local index = event == 1 and tonumber(value)
		if index and index % 1 == 0 and index >= 1 and index <= v.total then
			v = request(v, "jump", { index = index - 1 })
		end
	else
		local operation = ({ n = "next", p = "pass", f = "fail", s = "skip", r = "restart" })[key]
		local extra = {}
		if key == "f" or key == "s" then
			local note, event = ya.input { title = "Observation / skip reason (optional):", pos = { "center", w = 60 } }
			if event ~= 1 then
				return v
			end
			extra.note = note
		end
		v = request(v, operation, extra)
	end
	return v
end

function M:entry(job)
	if job.args[1] == "action" then
		local arguments = job.args[2]
		for k, value in pairs(job.args) do
			if type(k) == "string" then
				arguments = arguments .. " --" .. k .. "=" .. tostring(value)
			end
		end
		if action { "chezmoi", arguments } then
			ya.sleep(0.1)
			while not action_finished(false) do
				ya.sleep(0.05)
			end
			action_finished(true)
		end
		return
	elseif job.args[1] == "nav" then
		if job.args[2] == "4" then
			return select_long()
		end
		return navigate(job.args[2])
	end
	local v = lock()
	if not v then
		return ya.notify {
			title = "Manual guide",
			content = "An action or guide operation is still running.",
			timeout = 3,
			level = "warn",
		}
	end
	local old = v.root
	local ok, result = pcall(function()
		local result = controls(v, job.args[1] == "exit")
		if result.root ~= old then
			switch(result)
		end
		if result.token ~= v.token then
			result = request(result, "baseline")
		end
		return result
	end)
	if ok then
		release(result)
		if result.result.error then
			ya.notify { title = "Manual guide", content = result.result.error, timeout = 10, level = "error" }
		end
		if result.result.message then
			ya.notify { title = "Manual guide", content = result.result.message, timeout = 5 }
		end
	else
		local file = io.open(session .. "/manual-error.json", "w")
		if file then
			file:write(ya.json_encode { token = v.token, error = tostring(result) })
			file:close()
		end
		release()
		ya.notify {
			title = "Manual guide",
			content = tostring(result) .. ". Fixture retained; retry W.",
			timeout = 10,
			level = "error",
		}
	end
end

return M
