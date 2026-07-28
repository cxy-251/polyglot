-- polyglot-covers: lua.standalone.environment_initialization_isolation

local t = require("support.assertions")
local output_path = t.temp_path("init.out")
local error_path = t.temp_path("init.err")
local initialization = "error('LUA_INIT_5_5 must not run')"

local isolated = string.format(
    "LUA_INIT_5_5=%q lua -E -e 'print(42)' > %q 2> %q",
    initialization,
    output_path,
    error_path
)
t.truth(os.execute(isolated))
local output = assert(io.open(output_path, "r"))
t.equal(output:read("l"), "42")
t.truth(output:close())

local unisolated = string.format(
    "LUA_INIT_5_5=%q lua -e 'print(42)' > %q 2> %q",
    initialization,
    output_path,
    error_path
)
local ok, reason, status = os.execute(unisolated)
t.equal(ok, nil)
t.equal(reason, "exit")
t.truth(status ~= 0)

t.truth(os.remove(output_path))
t.truth(os.remove(error_path))
t.done()
