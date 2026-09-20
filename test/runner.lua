-- Fixture setup prefixes local python/script/pid_file/report values.
return {
	entry = function(_, job)
		local runner = require("chezmoi.process")
		local before = ya.time()
		local output, err = runner.run(python, { script, job.args[1], pid_file }, 0.25, 1048576)
		local file = assert(io.open(report, "w"))
		file:write(ya.json_encode { output = output, error = err, elapsed = ya.time() - before })
		file:close()
	end,
}
