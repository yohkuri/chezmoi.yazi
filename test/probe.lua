--- @sync entry
-- Fixture setup prefixes local report/dispatch paths after the annotation.
return {
	entry = function()
		local file = io.open(dispatch, "r")
		if file then
			local action = file:read("*a")
			file:close()
			os.remove(dispatch)
			ya.emit("plugin", { "runner", action })
		end
		local st = require("chezmoi")
		local rows = {}
		for _, file in ipairs(cx.active.current.files) do
			rows[tostring(file.url)] = Linemode:new(file):redraw():width()
		end
		local out = assert(io.open(report, "w"))
		out:write(ya.json_encode {
			records = st.records,
			rows = rows,
			destination = st.destination,
			running = st.running,
			action_busy = st.action_busy or false,
			epoch = st.epoch,
			signs = st.theme.signs,
			cwd = tostring(cx.active.current.cwd),
			instance = os.getenv("YAZI_ID"),
		})
		out:close()
	end,
}
