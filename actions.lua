-- Command policy, preflight queries, and argument construction, independent of Yazi's UI.
local core = require(".core")
local M = {}
-- recursive: takes --recursive. options: other accepted options; argv is built
-- in M.args. editable: targets need a source entry. root: may target the
-- destination root, which managed omits. confirm: when the plugin asks first.
-- effect: the summary line. menu and refresh are the plugin's own commands.
local commands = {
	menu = {},
	refresh = {},
	add = {
		recursive = true,
		options = { template = true, encrypt = true },
		confirm = "broad",
		effect = "Destination -> source (existing source entries may be replaced).",
	},
	["re-add"] = {
		recursive = true,
		root = true,
		confirm = "broad",
		effect = "Destination -> source. Templates and non-files are skipped by chezmoi.",
	},
	edit = {
		options = { apply = true },
		editable = true,
		effect = "Edit source entries; destination files are unchanged until apply.",
	},
	diff = { recursive = true, root = true, effect = "Preview source -> destination changes." },
	apply = {
		recursive = true,
		root = true,
		effect = "Source -> destination. Configured entry types, including scripts, are respected.",
	},
	forget = { editable = true, confirm = "always", effect = "Remove source entries; keep destination files." },
	destroy = {
		recursive = true,
		editable = true,
		confirm = "always",
		effect = "Permanently delete source AND destination entries.",
	},
}

function M.parse(args)
	local name = args[1] or "refresh"
	local command = commands[name]
	if not command then
		return nil,
			name == "remove" and "remove is unavailable. Use forget (keep files) or destroy (delete files)."
				or "Unknown chezmoi command. Use menu for available actions."
	end
	local action = { name = name, recursive = command.recursive }
	for key, value in pairs(args) do
		if key ~= 1 then
			local allowed = key == "recursive" and command.recursive or command.options and command.options[key]
			if not allowed or value ~= true and value ~= false and value ~= "true" and value ~= "false" then
				return nil, "Unsupported option: " .. tostring(key)
			end
			action[key] = value == true or value == "true"
		end
	end
	return action
end

-- Escape controls in UI text, never in the actual argument vector.
function M.display(path)
	return (path:gsub("\\", "\\\\"):gsub("[%z\1-\31\127]", function(c) return string.format("\\x%02x", c:byte()) end))
end

-- Without --recursive, chezmoi destroy still deletes a source directory's descendants.
local function shallow_destroy(action) return action.name == "destroy" and action.recursive == false end

-- Fresh chezmoi state for one action; a linemode marker is never evidence.
function M.facts(action, run)
	local facts = core.dirs(run)
	if not facts then
		return nil, "Cannot resolve chezmoi context. No action was run."
	end
	facts.managed = core.list_managed(run, facts.destination, "all", "none")
	if not facts.managed then
		return nil, "Cannot acquire managed targets. No action was run."
	end
	-- An index that was not queried stays absent, so prepare errors rather than trusts it.
	if commands[action.name].editable then
		facts.editable = core.list_managed(run, facts.destination, "files,symlinks,dirs", "externals")
		if not facts.editable then
			return nil, "Cannot acquire source entries. No action was run."
		end
	end
	if shallow_destroy(action) then
		-- Destination metadata can differ from the source tree destroy removes.
		facts.source_dirs = core.list_managed(run, facts.destination, "dirs", "externals")
		if not facts.source_dirs then
			return nil, "Cannot acquire source directories. No action was run."
		end
	end
	return facts
end

-- files carry fresh local metadata: local_path, exists, dir and special.
function M.prepare(action, files, facts)
	local command, destination, source, managed = commands[action.name], facts.destination, facts.source, facts.managed
	if #files == 0 then
		return nil, "No target. Select a file or hover over one."
	end
	local errors, targets, seen, broad = {}, {}, {}, false
	for _, file in ipairs(files) do
		local path, why = core.path(file.path), nil
		if not file.local_path or not path then
			why = "Only local paths are supported"
		elseif not core.inside(path, destination) then
			why = "Outside the destination directory"
		elseif core.inside(path, source) then
			why = "Source-tree actions are unsupported"
		elseif action.name == "destroy" and core.inside(source, path) then
			why = "Destroy target contains the source directory"
		elseif not file.exists then
			why = "Target is unavailable; select its parent to restore missing files"
		elseif file.special then
			why = "Unsupported file type"
		elseif action.name == "edit" and file.dir then
			why = "Select files inside the directory to edit"
		elseif shallow_destroy(action) and (file.dir or facts.source_dirs[path]) then
			why = "Non-recursive destroy cannot target a directory; chezmoi would still delete its descendants"
		elseif action.name ~= "add" and not managed[path] then
			-- The destination root itself is not listed by managed.
			local root = path == destination and command.root and action.recursive and next(managed)
			if not root then
				why = "Not managed by chezmoi"
			end
		end
		if not why and command.editable and not facts.editable[path] then
			why = "No editable source entry (external, removal, or script)"
		end
		if why then
			errors[#errors + 1] = why .. ": " .. M.display(file.path)
		elseif path and not seen[path] then
			seen[path] = true
			targets[#targets + 1] = { path = path, dir = file.dir }
			broad = #targets > 1 or broad or file.dir
		end
	end
	if #errors > 0 then
		return nil, table.concat(errors, "\n")
	end
	table.sort(targets, function(a, b) return a.path < b.path end)
	local minimal, directories = {}, {}
	for _, target in ipairs(targets) do
		local covered = false
		if (action.recursive or action.name == "forget") and next(directories) then
			local parent = target.path
			while parent and not covered do
				covered = directories[parent] or false
				parent = parent:match("^(.+)/[^/]+$") or parent ~= "/" and "/" or nil
			end
		end
		if not covered then
			minimal[#minimal + 1] = target
			if target.dir then
				directories[target.path] = true
			end
		end
	end
	return { action = action, targets = minimal, broad = broad }
end

function M.args(plan, opts, name)
	name = name or plan.action.name
	local args = core.context(opts)
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
	if commands[name].recursive then
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
	local confirm = commands[plan.action.name].confirm
	return confirm == "always" or confirm == "broad" and plan.broad
end

function M.summary(plan, name)
	name = name or plan.action.name
	local lines = { commands[name].effect, "Targets: " .. #plan.targets }
	for _, target in ipairs(plan.targets) do
		local scope = target.dir and (plan.action.recursive == false and " [directory only]" or " [including descendants]")
			or ""
		lines[#lines + 1] = M.display(target.path) .. scope
	end
	return table.concat(lines, "\n")
end

return M
