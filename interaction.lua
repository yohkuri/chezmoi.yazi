-- Async UI and fresh preflight for explicit user actions.
local actions = require(".actions")
local core = require(".core")
local process = require(".process")
local M = {}

function M.notify(content, level)
	ya.notify { title = "chezmoi", content = content, level = level or "warn", timeout = 7 }
end

local function choose(candidates)
	local cands = {}
	for _, c in ipairs(candidates) do
		cands[#cands + 1] = { on = c[1], desc = c[2] }
	end
	local selected = ya.which { cands = cands }
	return selected and candidates[selected][3]
end

function M.menu()
	local args = choose {
		{ "a", "Add", { "add" } },
		{ "o", "Add options", { "add-options" } },
		{ "r", "Re-add (skips templates and non-files)", { "re-add" } },
		{ "e", "Edit source files", { "edit" } },
		{ "E", "Edit and apply (with diff and confirmation)", { "edit", apply = true } },
		{ "d", "Diff", { "diff" } },
		{ "p", "Apply (with diff and confirmation)", { "apply" } },
		{ "f", "Forget (keep destination files)", { "forget" } },
		{ "x", "Destroy (delete source AND destination)", { "destroy" } },
		{ "R", "Refresh status", { "refresh" } },
	}
	if args and args[1] == "add-options" then
		args = choose {
			{ "t", "Add as template", { "add", template = true } },
			{ "e", "Add encrypted", { "add", encrypt = true } },
			{ "b", "Add encrypted template", { "add", template = true, encrypt = true } },
		}
	end
	return args and actions.parse(args)
end

local function confirm(plan, name)
	-- Review every target, including selections outside the visible directory.
	for first = 1, #plan.targets, 5 do
		local page = { action = plan.action, targets = {} }
		for i = first, math.min(first + 4, #plan.targets) do
			page.targets[#page.targets + 1] = plan.targets[i]
		end
		if
			not ya.confirm {
				pos = { "center", w = 76, h = 20 },
				title = "chezmoi "
					.. name
					.. " ("
					.. first
					.. "-"
					.. math.min(first + 4, #plan.targets)
					.. "/"
					.. #plan.targets
					.. ")",
				body = ui.Text(actions.summary(page, name) .. "\n\nContinue?"):wrap(ui.Wrap.YES),
			}
		then
			return false
		end
	end
	return true
end

local function preflight(snapshot, action)
	local run = process.client(snapshot.opts)
	local destination = run { "execute-template", "{{ .chezmoi.destDir }}" }
	local source = run { "execute-template", "{{ .chezmoi.sourceDir }}" }
	destination, source = core.path(destination), core.path(source)
	if not destination or not source then
		return nil, "Cannot resolve chezmoi context. No action was run."
	end
	local output = run { "managed", "--include=all", "--exclude=none", "--path-style=absolute", "--nul-path-separator" }
	local managed = output and core.managed(output, destination)
	if not managed then
		return nil, "Cannot acquire managed targets. No action was run."
	end
	local editable
	editable = {}
	if action.name == "edit" or action.name == "forget" or action.name == "destroy" then
		output = run {
			"managed",
			"--include=files,symlinks,dirs",
			"--exclude=externals",
			"--path-style=absolute",
			"--nul-path-separator",
		}
		editable = output and core.managed(output, destination)
		if not editable then
			return nil, "Cannot acquire source entries. No action was run."
		end
	end
	for _, file in ipairs(snapshot.files) do
		if file.local_path then
			local cha = fs.cha(Url(file.path), false)
			file.exists = cha ~= nil
			file.dir = cha and cha.is_dir and not cha.is_link or false
			file.special = cha and (cha.is_block or cha.is_char or cha.is_fifo or cha.is_sock) or false
		end
	end
	return actions.prepare(action, snapshot.files, destination, source, managed, editable)
end

function M.run(snapshot, action)
	local plan, err = preflight(snapshot, action)
	if not plan then
		M.notify(err)
		return
	end
	if actions.confirm_before(plan) and not confirm(plan, action.name) then
		return
	end
	local function execute(name)
		snapshot.executed = true
		local ok = process.interactive(snapshot.opts, actions.args(plan, snapshot.opts, name), actions.summary(plan, name))
		if not ok then
			M.notify("Command failed or was interrupted. Some changes may already have occurred; status will refresh.")
		end
		return ok
	end
	if action.name == "apply" or action.name == "edit" and action.apply then
		if action.name == "edit" and not execute("edit") then
			return
		end
		if not execute("diff") or not confirm(plan, "apply") then
			return
		end
		if not execute("apply") then
			return
		end
	elseif not execute(action.name) then
		return
	end
	M.notify("Command completed. Status will refresh; unchanged or skipped entries may remain.", "info")
end

return M
