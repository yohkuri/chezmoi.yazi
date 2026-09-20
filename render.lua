local M = {}
local defaults = {
	managed = { "C", "cyan" },
	unmanaged = { "", "darkgray" },
	clean = { " ", "green" },
	added = { "A", "green" },
	modified = { "M", "yellow" },
	deleted = { "D", "red" },
	run = { "R", "magenta" },
	changed = { "*", "yellow" },
	unknown = { "?", "darkgray" },
	error = { "!", "red" },
}
local code = { [" "] = "clean", A = "added", D = "deleted", M = "modified", R = "run" }

function M.theme()
	local t, result = th.chezmoi or {}, { signs = {}, styles = {}, widths = { 0, 0, 0 } }
	for key, def in pairs(defaults) do
		local sign = t[key .. "_sign"]
		if type(sign) ~= "string" or sign:find("[%z\1-\31\127]") then
			sign = def[1]
		end
		result.signs[key] = sign
		result.styles[key] = t[key] or ui.Style():fg(def[2])
	end
	result.styles.partial = t.partial or ui.Style():fg("yellow"):underline()
	result.styles.stale = t.stale or ui.Style():fg("darkgray"):dim()
	for slot, names in ipairs {
		{ "managed", "unmanaged", "unknown", "error" },
		{ "clean", "added", "modified", "deleted", "run", "unknown", "error" },
		{ "clean", "changed", "unknown", "error" },
	} do
		for _, name in ipairs(names) do
			result.widths[slot] = math.max(result.widths[slot], ui.Line(result.signs[name]):width())
		end
	end
	return result
end

function M.line(theme, record, dir, summary, hovered)
	local r = record or { membership = "unknown" }
	---@type (string|ui.Span)[]
	local spans = { " " }
	local function slot(name, width, style)
		local sign = name and theme.signs[name] or ""
		local span = ui.Span(sign .. string.rep(" ", width - ui.Line(sign):width()))
		if not hovered then
			span = span:style(theme.styles[r.stale and "stale" or style or name or "clean"])
		end
		spans[#spans + 1] = span
	end
	slot(r.membership, theme.widths[1])
	for i = 1, 2 do
		local name
		if r.membership == "managed" then
			name = r.failed and "error" or r.xy and code[r.xy:sub(i, i)] or "unknown"
		end
		slot(name, theme.widths[2])
	end
	if summary then
		local name = dir and (r.summary or (r.membership == "error" and "error" or "unknown")) or nil
		slot(name, theme.widths[3], r.partial and "partial" or nil)
	end
	return ui.Line(spans)
end

return M
