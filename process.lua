local actions = require(".actions")
local M = {}

-- stderr is deliberately discarded: besides containing secrets, read_line_with
-- can lose partial stdout when a concurrent stderr read wins (Yazi 26.9.1).
function M.run(command, args, timeout, limit, cancelled)
	local child = Command(command):arg(args):stdin(Command.NULL):stdout(Command.PIPED):stderr(Command.NULL):spawn()
	if not child then
		return nil, "spawn"
	end
	local deadline, chunks, size, eof = ya.time() + timeout, {}, 0, false
	local function stop(reason)
		child:start_kill()
		-- Never wait indefinitely after requesting termination.
		for _ = 1, 10 do
			if child:try_wait() then
				break
			end
			ya.sleep(0.01)
		end
		return nil, reason
	end
	while true do
		if cancelled and cancelled() then
			return stop("cancelled")
		end
		local remaining = deadline - ya.time()
		if remaining <= 0 then
			return stop("timeout")
		end
		if not eof then
			-- A read timeout fails the WHOLE query. Retrying a timed-out line read
			-- would silently discard the partial bytes consumed by read_until.
			local data, event = child:read_line_with { timeout = math.max(1, math.ceil(remaining * 1000)) }
			if event == 3 then
				return stop("timeout")
			end
			if event == 2 then
				eof = true
			elseif event == 0 then
				size = size + #data
				if size > limit then
					return stop("output_limit")
				end
				chunks[#chunks + 1] = data
			end
		else
			local status, err = child:try_wait()
			if status then
				if status.success then
					return table.concat(chunks)
				end
				return nil, "exit"
			elseif err then
				return stop("wait")
			end
			ya.sleep(math.min(0.01, remaining))
		end
	end
end

function M.client(opts, cancelled)
	return function(args)
		local all = {
			"--no-tty",
			"--no-pager",
			"--color=false",
			"--progress=false",
			"--skip-secrets=false",
		}
		for _, arg in ipairs(actions.context(opts)) do
			all[#all + 1] = arg
		end
		for _, arg in ipairs(args) do
			all[#all + 1] = arg
		end
		return M.run(opts.command, all, opts.timeout, opts.output_limit, cancelled)
	end
end

-- Interactive commands own the terminal until the user has read their output.
-- The shell only implements the fixed Enter prompt; target paths never enter it.
function M.interactive(opts, args, summary)
	local permit = ui.hide()
	local ok, success = pcall(function()
		io.write("\27[2J\27[Hchezmoi\n" .. summary .. "\n\n")
		io.flush()
		local status =
			Command(opts.command):arg(args):stdin(Command.INHERIT):stdout(Command.INHERIT):stderr(Command.INHERIT):status()
		io.write(
			status and ("\nchezmoi exited with code " .. tostring(status.code) .. ".\n")
				or "\nCould not start or wait for chezmoi.\n"
		)
		io.flush()
		local resumed = Command("/bin/sh")
			:arg({ "-c", 'printf "Press Enter to return to Yazi... "; IFS= read -r reply' })
			:stdin(Command.INHERIT)
			:stdout(Command.INHERIT)
			:stderr(Command.INHERIT)
			:status()
		return status and status.success and resumed and resumed.success or false
	end)
	permit:drop()
	return ok and success or false
end

return M
