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

-- A command can leave the terminal raw, where Enter no longer ends a line and
-- a newline no longer returns the cursor, and keys typed while it ran stay
-- queued and would answer the prompt unread. RESTORE drops what is queued and
-- puts back the mode saved before the command, which reaches the shell as "$1"
-- and never as source; if that fails, it at least ends the read without minimum.
local RESTORE = 'stty -icanon min 0 time 0 && cat >/dev/null; stty "$1" || stty icanon'
-- A command can also leave modes that the terminal, not stty, keeps: a color,
-- which would fill the next action's cleared screen and stay after Yazi exits, a
-- hidden cursor, mouse reports or bracketed paste echoed into the prompt, keys
-- encoded so that Enter or Ctrl-C no longer reach it (kitty flags,
-- modifyOtherKeys), and a line-drawing character set.
local RESET = "\27[0m\27[?25h\27[?1000l\27[?1002l\27[?1003l\27[?1006l\27[?2004l\27[<99u\27[>4;0m\27(B"
-- After Enter, an echoed newline has moved the cursor below the prompt, so step
-- back and erase only the prompt's own line; the output stays. With echo off, or
-- no stty to tell, the prompt stays rather than erase a line of output.
local PROMPT = 'printf "Press Enter to return to Yazi... "; IFS= read -r reply || exit; '
	.. "s=$(stty -a 2>/dev/null) || exit 0; "
	.. 'case " $s " in *[[:space:]]-echo[[:space:]]*) ;; *) printf "\\r\\033[A\\033[J" ;; esac'

-- Interactive commands own the terminal until the user has read their output.
-- Fixed shell snippets only restore the terminal and implement the Enter prompt;
-- executable arguments and target paths never enter them.
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
		if mode then
			Command("/bin/sh")
				:arg({ "-c", RESTORE, "sh", mode })
				:stdin(Command.INHERIT)
				:stdout(Command.NULL)
				:stderr(Command.NULL)
				:status()
		end
		io.write(
			RESET,
			status and ("\nchezmoi exited with code " .. tostring(status.code) .. ".\n")
				or "\nCould not start or wait for chezmoi.\n"
		)
		io.flush()
		local resumed = Command("/bin/sh")
			:arg({ "-c", PROMPT })
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
