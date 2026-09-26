-- Command policy and argument construction, independent of Yazi's UI.
local core = require(".core")
local M = {}
local commands = {
	menu = true,
	refresh = true,
	add = true,
	["re-add"] = true,
	edit = true,
	diff = true,
	apply = true,
	forget = true,
	destroy = true,
}
local recursive = { add = true, ["re-add"] = true, diff = true, apply = true, destroy = true }

function M.parse(args)
	local name = args[1] or "refresh"
	if not commands[name] then
		return nil,
			name == "remove" and "remove is unavailable. Use forget (keep files) or destroy (delete files)."
				or "Unknown chezmoi command. Use menu for available actions."
	end
	local action = { name = name, recursive = recursive[name] and true or nil }
	for key, value in pairs(args) do
		if key ~= 1 then
			local allowed = key == "recursive" and recursive[name]
				or (key == "template" or key == "encrypt") and name == "add"
				or key == "apply" and name == "edit"
			if not allowed or value ~= true and value ~= false and value ~= "true" and value ~= "false" then
				return nil, "Unsupported option: " .. tostring(key)
			end
			action[key] = value == true or value == "true"
		end
	end
	return action
end

function M.context(opts)
	local args = {}
	for _, key in ipairs { "config", "source", "destination", "persistent_state", "cache" } do
		if opts[key] then
			args[#args + 1], args[#args + 2] = "--" .. key:gsub("_", "-"), opts[key]
		end
	end
	return args
end

-- Escape controls in UI text, never in the actual argument vector.
function M.display(path)
	return (path:gsub("\\", "\\\\"):gsub("[%z\1-\31\127]", function(c) return string.format("\\x%02x", c:byte()) end))
end

function M.prepare(action, files, destination, source, managed, editable)
	if #files == 0 then
		return nil, "No target. Select a file or hover over one."
	end
	local errors, targets, seen = {}, {}, {}
	for _, file in ipairs(files) do
		local path, why = core.path(file.path), nil
		if not file.local_path or not path then
			why = "Only local paths are supported"
		elseif not core.inside(path, destination) then
			why = "Outside the destination directory"
		elseif core.inside(path, source) then
			why = "Source-tree actions are unsupported"
		elseif not file.exists then
			why = "Target is unavailable; select its parent to restore missing files"
		elseif file.special then
			why = "Unsupported file type"
		elseif action.name == "edit" and file.dir then
			why = "Select files inside the directory to edit"
		elseif action.name == "destroy" and action.recursive == false and file.dir then
			why = "Non-recursive destroy cannot target a directory; chezmoi would still delete its descendants"
		elseif action.name ~= "add" and not managed[path] then
			-- The destination root itself is not listed by managed.
			local root = path == destination
				and (action.name == "diff" or action.name == "apply" or action.name == "re-add")
				and action.recursive
				and next(managed)
			if not root then
				why = "Not managed by chezmoi"
			end
		end
		if
			not why
			and (action.name == "edit" or action.name == "forget" or action.name == "destroy")
			and not editable[path]
		then
			why = "No editable source entry (external, removal, or script)"
		end
		if why then
			errors[#errors + 1] = why .. ": " .. M.display(file.path)
		elseif path and not seen[path] then
			seen[path] = true
			targets[#targets + 1] = { path = path, dir = file.dir }
		end
	end
	if #errors > 0 then
		return nil, table.concat(errors, "\n")
	end
	local broad = #targets > 1
	for _, target in ipairs(targets) do
		broad = broad or target.dir
	end
	table.sort(targets, function(a, b) return a.path < b.path end)
	local minimal = {}
	for _, target in ipairs(targets) do
		local covered = false
		if action.recursive or action.name == "forget" then
			for _, parent in ipairs(minimal) do
				if parent.dir and core.inside(target.path, parent.path) then
					covered = true
					break
				end
			end
		end
		if not covered then
			minimal[#minimal + 1] = target
		end
	end
	return { action = action, targets = minimal, broad = broad }
end

function M.args(plan, opts, name)
	name = name or plan.action.name
	local args = M.context(opts)
	args[#args + 1] = name
	-- The plugin owns the separate preview/confirmation/apply stages.
	if name == "edit" then
		args[#args + 1], args[#args + 2] = "--apply=false", "--watch=false"
	end
	-- apply has no diff.include/exclude configuration. Its preview must not
	-- silently omit entries hidden by the standalone diff configuration.
	if name == "apply" or name == "diff" and (plan.action.name == "apply" or plan.action.apply) then
		args[#args + 1], args[#args + 2] = "--include=all", "--exclude=none"
	end
	if recursive[name] then
		args[#args + 1] = "--recursive=" .. tostring(plan.action.recursive ~= false)
	end
	if name == "add" then
		for _, flag in ipairs { "template", "encrypt" } do
			if plan.action[flag] then
				args[#args + 1] = "--" .. flag
			end
		end
	end
	args[#args + 1] = "--"
	for _, target in ipairs(plan.targets) do
		args[#args + 1] = target.path
	end
	return args
end

function M.confirm_before(plan)
	local name = plan.action.name
	return name == "forget" or name == "destroy" or (name == "add" or name == "re-add") and plan.broad
end

function M.summary(plan, name)
	name = name or plan.action.name
	local effects = {
		add = "Destination -> source (existing source entries may be replaced).",
		["re-add"] = "Destination -> source. Templates and non-files are skipped by chezmoi.",
		forget = "Remove source entries; keep destination files.",
		destroy = "Permanently delete source AND destination entries.",
		apply = "Source -> destination. Configured entry types, including scripts, are respected.",
		edit = "Edit source entries; destination files are unchanged until apply.",
		diff = "Preview source -> destination changes.",
	}
	local lines = { effects[name], "Targets: " .. #plan.targets }
	for _, target in ipairs(plan.targets) do
		local scope = target.dir and (plan.action.recursive == false and " [directory only]" or " [including descendants]")
			or ""
		lines[#lines + 1] = M.display(target.path) .. scope
	end
	return table.concat(lines, "\n")
end

return M
