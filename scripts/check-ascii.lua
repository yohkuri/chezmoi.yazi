-- Commit messages are ASCII English, including bodies and footers.
-- This also makes commitlint's character lengths equal display columns.
local message = io.read("*a")
if message:find("[^\9\10\13\32-\126]") then
	io.stderr:write("Commit messages must contain printable ASCII, tabs, and newlines only.\n")
	os.exit(1)
end
