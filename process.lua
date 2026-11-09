local core = require(".core")
local M = {}

-- stderr is deliberately discarded: besides containing secrets, read_line_with
-- can lose partial stdout when a concurrent stderr read wins (Yazi 26.9.1).
function M.run(command, args, timeout, limit, cancelled)
	if cancelled and cancelled() then
		return nil, "cancelled"
	end
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
	local context = core.context(opts)
	return function(args)
		local all = {
			"--no-tty",
			"--no-pager",
			"--color=false",
			"--progress=false",
			"--skip-secrets=false",
		}
		for _, arg in ipairs(context) do
			all[#all + 1] = arg
		end
		for _, arg in ipairs(args) do
			all[#all + 1] = arg
		end
		return M.run(opts.command, all, opts.timeout, opts.output_limit, cancelled)
	end
end

local PROMPT = 'printf "Press Enter to return to Yazi... "; IFS= read -r reply'
-- A command can leave the terminal raw, where Enter no longer ends a line and
-- a newline no longer returns the cursor, and keys typed while it ran stay
-- queued and would answer the prompt unread. RESTORE drops what is queued and
-- puts back the mode saved before the command, which reaches the shell as "$1"
-- and never as source.
local RESTORE = 'stty -icanon min 0 time 0 && cat >/dev/null; stty "$1"'
-- With the mode restored, Enter's echo moves the cursor below the prompt, so
-- step back and erase only the prompt's own line; the output stays. Without it
-- the echo is unknown, and the prompt stays rather than erase a line of output.
local ERASE = ' && printf "\\r\\033[A\\033[J"'

-- Interactive commands own the terminal until the user has read their output.
-- The shell only implements the fixed Enter prompt; target paths never enter it.
function M.interactive(opts, name, args, summary)
	local permit = ui.hide()
	local ok, success = pcall(function()
		local argv = { opts.command }
		for _, arg in ipairs(args) do
			argv[#argv + 1] = arg
		end
		local saved =
			Command("stty"):arg({ "-g" }):stdin(Command.INHERIT):stdout(Command.PIPED):stderr(Command.NULL):output()
		local mode = saved and saved.status.success and saved.stdout:match("^(%S+)%s*$")
		-- JSON quoting preserves argument boundaries and makes control paths readable.
		io.write(
			"\27[2J\27[Hchezmoi " .. name .. "\n" .. summary .. "\n\nRunning (argv):\n" .. ya.json_encode(argv) .. "\n\n"
		)
		io.flush()
		local status =
			Command(opts.command):arg(args):stdin(Command.INHERIT):stdout(Command.INHERIT):stderr(Command.INHERIT):status()
		local restored = mode
			and Command("/bin/sh")
				:arg({ "-c", RESTORE, "sh", mode })
				:stdin(Command.INHERIT)
				:stdout(Command.NULL)
				:stderr(Command.NULL)
				:status()
		-- A color the command left would otherwise fill the next action's screen,
		-- and the terminal after Yazi exits.
		io.write(
			"\27[0m"
				.. (
					status and ("\nchezmoi exited with code " .. tostring(status.code) .. ".\n")
					or "\nCould not start or wait for chezmoi.\n"
				)
		)
		io.flush()
		local resumed = Command("/bin/sh")
			:arg({ "-c", restored and restored.success and PROMPT .. ERASE or PROMPT })
			:stdin(Command.INHERIT)
			:stdout(Command.INHERIT)
			:stderr(Command.INHERIT)
			:status()
		return status and status.success and resumed and resumed.success or false
	end)
	permit:drop()
	return ok and success
end

return M
