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

local function guide_lines(v, width)
	local title = string.format("%d/%d %s - step %d/%d", v.case, v.total, v.title, v.step, v.steps)
	local lines
	if v.finished then
		local counts = {}
		for _, result in ipairs(v.results) do
			counts[result] = (counts[result] or 0) + 1
		end
		local totals = {}
		for _, result in ipairs { "PASS", "FAIL", "ERROR", "SKIP", "NOT RUN" } do
			totals[#totals + 1] = result .. ": " .. (counts[result] or 0)
		end
		lines =
			{ "Walk complete - q: results and finish", table.concat(totals, " | "), "W/d: case results and command history" }
	else
		lines = { title, v.instruction, summary(v) }
		if v.result.message then
			lines[#lines + 1] = v.result.message
		end
	end
	return ui.lines(table.concat(lines, "\n"), { width = math.max(1, width), wrap = ui.Wrap.YES, tab_size = 4 })
end

function M:setup()
	-- Capture the new process epoch before a resumed step can run actions.
	self.view, self.hidden, self.busy = initial, false, initial.needs_baseline
	local layout, build = Root.layout, Root.build
	local guide = { _id = "manual-guide" }
	function guide:new(area) return setmetatable({ _area = area }, { __index = self }) end
	function guide:reflow() return { self } end
	function guide:redraw()
		local v = M.view
		local lines = {}
		local controls = v.finished and "q: results and finish | W: controls"
			or "P: PASS/check/next | S: SKIP/next | W: controls"
		if not v.finished and self._area.w < 60 then
			controls = "P: PASS | S: SKIP | W: controls"
		end
		if M.busy then
			controls = "Preparing/checking..."
		end
		if self._area.h == 1 then
			lines[1] = ui.Line(controls)
		else
			local content = M.guide_content
			for i = 1, math.min(#content, self._area.h - 1) do
				lines[#lines + 1] = content[i]
			end
			if #content > self._area.h - 1 then
				lines[self._area.h - 1] = ui.Line("W/d: full instructions and command history")
			end
			lines[self._area.h] = ui.Line(controls)
		end
		local text = ui.Text(lines):wrap(ui.Wrap.NO)
		text:area(self._area)
		return { text }
	end
	function Root:layout()
		if M.hidden then
			return layout(self)
		end
		M.guide_content = self._area.h < 20 and {} or guide_lines(M.view, self._area.w)
		local height = self._area.h < 20 and 1 or math.min(#M.guide_content + 1, math.floor(self._area.h / 2))
		self._chunks = Layout()
			:direction(Layout.VERTICAL)
			:constraints({
				ui.Constraint.Length(1),
				ui.Constraint.Length(Tabs.height()),
				ui.Constraint.Fill(1),
				ui.Constraint.Length(height),
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
	if self.busy then
		ya.emit("plugin", { "manual", "baseline" })
	end
end

local lock = ya.sync(function(st, verdict, baseline)
	if verdict then
		local now, previous = ya.time(), st.verdict_at
		st.verdict_at = now
		if previous and now - previous < 0.75 then
			return nil
		end
	end
	if (st.busy and not baseline) or st.action_pending or require("chezmoi").action_busy then
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
local snapshot = ya.sync(function(_, full)
	local st = require("chezmoi")
	local result = {
		epoch = st.epoch,
		running = st.running or false,
	}
	if full then
		result.records = st.records
		result.signs = st.theme.signs
		result.cwd = tostring(cx.active.current.cwd)
		result.action_busy = st.action_busy or false
	end
	return result
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
	payload.token = v.token
	local checking = operation == "accept" or operation == "fail" or operation == "check"
	local answered = v.result.visual == "PASS" or v.result.visual == "FAIL" or v.result.visual == "SKIP"
	if checking then
		local deadline = ya.time() + 8
		while snapshot().running and ya.time() < deadline do
			ya.sleep(0.05)
		end
	end
	if checking or operation == "next" and not answered then
		payload.snapshot = snapshot(true)
	elseif operation == "baseline" then
		payload.snapshot = { epoch = snapshot().epoch }
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
				{ on = "d", desc = "Results and diagnostics" },
				{ on = "k", desc = "Save, retain fixtures and exit" },
				{ on = "c", desc = "Save and exit; clean fixtures unless any attempt failed" },
			}
		or {
			{ on = "n", desc = "Next step (requires visual verdict or skip)" },
			{ on = "p", desc = "PASS, check and next (same as P)" },
			{ on = "f", desc = "Record visual FAIL" },
			{ on = "s", desc = "Skip current step" },
			{ on = "r", desc = "Restart case with fresh fixture" },
			{ on = "j", desc = "Jump to case" },
			{ on = "d", desc = "Full instructions, results, files and logs" },
			{ on = "h", desc = "Hide/show guide (normal layout)" },
			{ on = "q", desc = "Results and finish" },
		}
	local choice = ya.which { cands = keys }
	if not choice then
		return v
	end
	local key = keys[choice].on
	if key == "d" then
		if not v.finished then
			v = request(v, "check")
		end
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
		local operation = ({ n = "next", p = "accept", f = "fail", s = "skip", r = "restart" })[key]
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
	local verdict = job.args[1] == "accept" or job.args[1] == "skip-next"
	local baseline = job.args[1] == "baseline"
	local v = lock(verdict, baseline)
	if not v then
		if verdict then
			return
		end
		return ya.notify {
			title = "Manual guide",
			content = "An action or guide operation is still running.",
			timeout = 3,
			level = "warn",
		}
	end
	local ok, result = pcall(function()
		if baseline then
			return request(v, "baseline")
		end
		if verdict and v.finished then
			return v
		end
		local result
		if verdict then
			result = request(v, job.args[1])
		else
			result = controls(v, job.args[1] == "exit")
		end
		if result.root ~= v.root then
			switch(result)
		end
		if result.token ~= v.token and result.needs_baseline then
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
		local file = io.open(session .. "/manual-errors.jsonl", "a")
		if file then
			file:write(ya.json_encode { token = v.token, error = tostring(result) }, "\n")
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
