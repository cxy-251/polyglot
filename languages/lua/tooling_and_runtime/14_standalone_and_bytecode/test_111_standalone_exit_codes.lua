-- polyglot-covers: lua.standalone.exit_codes

local t = require("support.assertions")
local error_path = t.temp_path("standalone.err")

local ok, reason, status = os.execute("lua -E -e 'os.exit(7)'")
t.equal(ok, nil)
t.equal(reason, "exit")
t.equal(status, 7)

ok, reason, status = os.execute(
    string.format("lua -E -e 'error(\"boom\")' 2> %q", error_path)
)
t.equal(ok, nil)
t.equal(reason, "exit")
t.truth(status ~= 0)

local error_file = assert(io.open(error_path, "r"))
t.matches(error_file:read("a"), "boom")
t.truth(error_file:close())
t.truth(os.remove(error_path))

t.done()
