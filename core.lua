-- Pure parsing, query planning, and reduction. No Yazi globals or filesystem I/O.
local M = {}

function M.path(s)
	if type(s) ~= "string" or s:sub(1, 1) ~= "/" or s:find("\0", 1, true) then
		return nil
	end
	local parts = {}
	for p in s:gmatch("[^/]+") do
		if p == ".." then
			table.remove(parts)
		elseif p ~= "." then
			parts[#parts + 1] = p
		end
	end
	return "/" .. table.concat(parts, "/")
end

function M.inside(path, root)
	return path == root or path:sub(1, #root + (root == "/" and 0 or 1)) == root .. (root == "/" and "" or "/")
end

function M.managed(output, destination)
	local index = {}
	if output ~= "" and output:sub(-1) ~= "\0" then
		return nil, "parse"
	end
	for path in output:gmatch("([^%z]+)%z") do
		local normalized = M.path(path)
		if not normalized or not M.inside(normalized, destination) or index[normalized] then
			return nil, "parse"
		end
		index[normalized] = true
	end
	if output:find("\0\0", 1, true) or output:sub(1, 1) == "\0" then
		return nil, "parse"
	end
	return index
end

local function pair(s) return #s == 2 and s:sub(1, 1):match("^[ ADM]$") and s:sub(2, 2):match("^[ ADMR]$") and s ~= "  " end

function M.status(output, coverage, exceptional)
	local result = {}
	if exceptional then
		if output == "" then
			return result
		end
		if not pair(output:sub(1, 2)) or output:sub(3) ~= " " .. exceptional .. "\n" then
			return nil, "parse"
		end
		result[exceptional] = output:sub(1, 2)
		return result
	end
	if output ~= "" and output:sub(-1) ~= "\n" then
		return nil, "parse"
	end
	for line in output:gmatch("([^\n]*)\n") do
		local xy, path = line:sub(1, 2), line:sub(4)
		if line:sub(3, 3) ~= " " or not pair(xy) or not coverage[path] or result[path] then
			return nil, "parse"
		end
		result[path] = xy
	end
	return result
end

function M.chunks(paths, budget)
	local chunks, chunk, size = {}, {}, 0
	for _, path in ipairs(paths) do
		if #chunk > 0 and size + #path + 1 > budget then
			chunks[#chunks + 1], chunk, size = chunk, {}, 0
		end
		chunk[#chunk + 1], size = path, size + #path + 1
	end
	if #chunk > 0 then
		chunks[#chunks + 1] = chunk
	end
	return chunks
end

local function keys(t)
	local a = {}
	for k in pairs(t) do
		a[#a + 1] = k
	end
	table.sort(a)
	return a
end

function M.failed(files, reason)
	local records = {}
	for _, file in ipairs(files) do
		records[file.path] = { membership = "error", reason = reason }
	end
	return { records = records, error = reason }
end

-- run(args) returns stdout or nil plus a sanitized failure category.
function M.collect(files, opts, run)
	local destination, err = run { "execute-template", "{{ .chezmoi.destDir }}" }
	destination = destination and M.path(destination)
	if not destination then
		return M.failed(files, err or "parse")
	end
	local output
	output, err = run {
		"managed",
		"--include=all",
		"--exclude=none",
		"--path-style=absolute",
		"--nul-path-separator",
	}
	local index
	if output then
		index, err = M.managed(output, destination)
	end
	if not index then
		local failed = M.failed(files, err)
		failed.destination = destination
		return failed
	end

	local roots, wanted = {}, {}
	for _, file in ipairs(files) do
		if index[file.path] then
			roots[file.path], wanted[file.path] = true, true
		end
		if opts.directory_summary and file.dir then
			for path in pairs(index) do
				if M.inside(path, file.path) then
					wanted[path] = true
					if not index[file.path] then
						roots[path] = true
					end
				end
			end
		end
	end
	-- Collapse overlapping roots. Every requested descendant is still in coverage.
	local minimal = {}
	for _, path in ipairs(keys(roots)) do
		local covered = false
		if opts.directory_summary then
			for _, root in ipairs(minimal) do
				if M.inside(path, root) then
					covered = true
					break
				end
			end
		end
		if not covered then
			minimal[#minimal + 1] = path
		end
	end

	local values, retries, last_error = {}, opts.max_retries, nil
	local function query(paths, recursive, recovery)
		if #paths == 0 then
			return
		end
		local coverage = {}
		for path in pairs(wanted) do
			for _, root in ipairs(paths) do
				if path == root or recursive and M.inside(path, root) then
					coverage[path] = true
					break
				end
			end
		end
		if recovery then
			if retries <= 0 then
				return
			end
			retries = retries - 1
		end
		local args = {
			"status",
			"--include=all",
			"--exclude=none",
			"--path-style=absolute",
			"--recursive=" .. tostring(recursive),
			"--",
		}
		for _, path in ipairs(paths) do
			args[#args + 1] = path
		end
		local data, why = run(args)
		local parsed
		if data then
			local exceptional = #paths == 1 and not recursive and paths[1]:find("[\r\n]") and paths[1] or nil
			parsed, why = M.status(data, coverage, exceptional)
		end
		if parsed then
			for path in pairs(coverage) do
				values[path] = parsed[path] or "  "
			end
			return
		end
		last_error = why or "query"
		-- Only retry failures that can be isolated. Do not multiply timeouts/spawn failures.
		if why ~= "exit" and why ~= "parse" then
			return
		end
		local all = keys(coverage)
		if not recursive and #all <= 1 then
			return
		end
		local mid = math.ceil(#all / 2)
		local left, right = {}, {}
		for i, path in ipairs(all) do
			local half = i <= mid and left or right
			half[#half + 1] = path
		end
		return left, right
	end
	local execute
	execute = function(paths, recursive, recovery)
		-- A failed recursive root can expand into many explicit descendants.
		-- Recovery must respect both the argument and extra-query budgets.
		if recovery then
			local chunks = M.chunks(paths, opts.argument_bytes)
			if #chunks > 1 then
				for _, chunk in ipairs(chunks) do
					execute(chunk, recursive, true)
				end
				return
			end
		end
		local left, right = query(paths, recursive, recovery)
		if left then
			execute(left, false, true)
			execute(right, false, true)
		end
	end

	-- No recursive query may hide a newline-containing descendant in its output.
	local special = false
	for path in pairs(wanted) do
		if path:find("[\r\n]") then
			special = true
			break
		end
	end
	if special then
		local ordinary = {}
		for _, path in ipairs(keys(wanted)) do
			if path:find("[\r\n]") then
				execute({ path }, false, false)
			else
				ordinary[#ordinary + 1] = path
			end
		end
		for _, chunk in ipairs(M.chunks(ordinary, opts.argument_bytes)) do
			execute(chunk, false, false)
		end
	else
		for _, chunk in ipairs(M.chunks(minimal, opts.argument_bytes)) do
			execute(chunk, opts.directory_summary, false)
		end
	end

	local records, incomplete = {}, false
	for _, file in ipairs(files) do
		local r = { membership = index[file.path] and "managed" or "unmanaged" }
		if index[file.path] then
			r.xy, r.failed = values[file.path], not values[file.path]
			incomplete = incomplete or r.failed
		end
		if opts.directory_summary and file.dir then
			local changed, complete = false, true
			for path in pairs(wanted) do
				if path ~= file.path and M.inside(path, file.path) then
					if not values[path] then
						complete = false
					elseif values[path] ~= "  " then
						changed = true
					end
				end
			end
			r.summary = changed and "changed" or complete and "clean" or "error"
			r.partial = changed and not complete
			incomplete = incomplete or not complete
		end
		records[file.path] = r
	end
	return {
		records = records,
		destination = destination,
		error = incomplete and (last_error or "query") or nil,
	}
end

return M
