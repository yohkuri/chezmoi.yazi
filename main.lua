--- @since 26.9.1

local core = require(".core")
local process = require(".process")
local render = require(".render")
local M = {}

local function current_files()
	local files = {}
	if not cx then
		return files
	end
	for _, file in ipairs(cx.active.current.files) do
		local path = core.path(tostring(file.url))
		if path then
			files[#files + 1] = { path = path, dir = file.cha.is_dir }
		end
	end
	return files
end

local function enqueue(st, files, force)
	if not st.opts then
		return
	end
	if force then
		st.epoch = st.epoch + 1
		st.pending, st.records = {}, {}
	end
	local now = ya.time()
	for _, file in ipairs(files) do
		local old = st.records[file.path]
		local inflight = st.inflight_epoch == st.epoch and st.inflight and st.inflight[file.path]
		if not inflight and (not old or now >= (old.retry_at or 0)) then
			st.pending[file.path] = file
		end
	end
	if not st.running and next(st.pending) then
		st.running = true
		ya.emit("plugin", { "chezmoi", "work" })
	end
	if force then
		ui.render()
	end
end

-- All cross-context blocks live here, unconditionally, in a fixed order.
local submit = ya.sync(function(st, files, force)
	local current = current_files()
	if force then
		files = current
	else
		local visible, filtered = {}, {}
		for _, file in ipairs(current) do
			visible[file.path] = true
		end
		for _, file in ipairs(files) do
			if visible[file.path] then
				filtered[#filtered + 1] = file
			end
		end
		files = filtered
	end
	enqueue(st, files, force)
end)

local claim = ya.sync(function(st)
	if st.worker_active then
		return false
	end
	st.worker_active = true
	return true
end)

local take = ya.sync(function(st)
	if not st.opts or not next(st.pending) then
		st.running, st.worker_active, st.inflight = false, false, nil
		return nil
	end
	local files = {}
	for path, file in pairs(st.pending) do
		files[#files + 1] = file
		if st.records[path] then
			st.records[path].stale = true
		end
	end
	st.inflight, st.inflight_epoch, st.pending = st.pending, st.epoch, {}
	ui.render()
	return { files = files, opts = st.opts, epoch = st.epoch }
end)

local cancelled = ya.sync(function(st, epoch) return st.epoch ~= epoch end)

local publish = ya.sync(function(st, work, result)
	st.inflight = nil
	if work.epoch ~= st.epoch then
		return
	end
	local now = ya.time()
	if result.destination and st.destination ~= result.destination then
		st.records, st.destination = {}, result.destination
	end
	for path, record in pairs(result.records) do
		record.retry_at = now + (result.error and st.opts.error_backoff or st.opts.cache_ttl)
		st.records[path] = record
	end
	if result.error and result.error ~= "cancelled" then
		if now >= (st.notified_at or 0) + 30 then
			st.notified_at = now
			ya.notify {
				title = "chezmoi",
				content = "Status unavailable (" .. result.error .. "). Use refresh to retry.",
				level = "warn",
				timeout = 5,
			}
		end
	end
	ui.render()
end)

function M:setup(opts)
	opts = opts or {}
	if ya.target_family() == "windows" then
		error("chezmoi.yazi currently supports local Unix paths")
	end
	local defaults = {
		command = "chezmoi",
		order = 1600,
		directory_summary = true,
		timeout = 10,
		cache_ttl = 2,
		error_backoff = 10,
		max_retries = 8,
		argument_bytes = 8192,
		output_limit = 16 * 1024 * 1024,
	}
	for key, value in pairs(opts) do
		if
			defaults[key] == nil
			and not ({
				config = true,
				source = true,
				destination = true,
				persistent_state = true,
				cache = true,
			})[key]
		then
			error("Unknown chezmoi option: " .. tostring(key))
		end
		defaults[key] = value
	end
	for _, key in ipairs {
		"order",
		"timeout",
		"cache_ttl",
		"error_backoff",
		"max_retries",
		"argument_bytes",
		"output_limit",
	} do
		local n = defaults[key]
		if type(n) ~= "number" or n ~= n or n == math.huge or n < 0 then
			error("Invalid chezmoi option: " .. key)
		end
	end
	for _, key in ipairs { "order", "max_retries", "argument_bytes", "output_limit" } do
		if defaults[key] % 1 ~= 0 then
			error("Invalid chezmoi option: " .. key)
		end
	end
	if defaults.timeout == 0 or defaults.argument_bytes < 256 or defaults.output_limit < 1024 then
		error("Invalid chezmoi process limits")
	end
	if type(defaults.directory_summary) ~= "boolean" then
		error("directory_summary must be boolean")
	end
	for _, key in ipairs { "command", "config", "source", "destination", "persistent_state", "cache" } do
		local value = defaults[key]
		if value ~= nil and (type(value) ~= "string" or value == "" or value:find("\0", 1, true)) then
			error("Invalid chezmoi option: " .. key)
		end
	end
	self.opts, self.records, self.pending, self.epoch = defaults, {}, {}, (self.epoch or 0) + 1
	self.theme = render.theme()
	if self.child_id then
		Linemode:children_remove(self.child_id)
	end
	self.child_id = Linemode:children_add(function(row)
		if not row._file.in_current then
			return ""
		end
		local path = core.path(tostring(row._file.url))
		if not path or self.destination and not core.inside(path, self.destination) then
			return ""
		end
		return render.line(
			self.theme,
			self.records[path],
			row._file.cha.is_dir,
			self.opts.directory_summary,
			row._file.is_hovered
		)
	end, defaults.order)
	if not self.subscribed then
		self.subscribed = true
		ps.sub("theme", function()
			self.theme = render.theme()
			ui.render()
		end)
		ps.sub("cd", function() enqueue(self, current_files(), true) end)
	end
	enqueue(self, current_files(), true)
end

function M:fetch(job)
	local files = {}
	for _, file in ipairs(job.files) do
		local path = core.path(tostring(file.url))
		if path then
			files[#files + 1] = { path = path, dir = file.cha.is_dir }
		end
	end
	submit(files, false)
	return ya.co(function()
		for _, file in ipairs(job.files) do
			coroutine.yield(file, { retry = true })
		end
	end)
end

function M:entry(job)
	local action = job.args[1] or "refresh"
	if action == "refresh" then
		return submit({}, true)
	end
	if action ~= "work" then
		return ya.notify {
			title = "chezmoi",
			content = "Unknown command. Use: plugin chezmoi -- refresh",
			level = "warn",
			timeout = 5,
		}
	end
	if not claim() then
		return
	end
	while true do
		local work = take()
		if not work then
			return
		end
		local run = process.client(work.opts, function() return cancelled(work.epoch) end)
		local ok, result = pcall(core.collect, work.files, work.opts, run)
		if not ok then
			result = core.failed(work.files, "internal")
		end
		publish(work, result)
	end
end

return M
