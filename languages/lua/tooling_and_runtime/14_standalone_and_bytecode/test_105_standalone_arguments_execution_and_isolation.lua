-- polyglot-covers: lua.standalone.arguments_execution_and_isolation

local t = require("support.assertions")
local script_path = t.temp_path("arguments.lua")
local output_path = t.temp_path("standalone.out")
local error_path = t.temp_path("standalone.err")
local file = assert(io.open(script_path, "w"))
assert(file:write([[print(arg[0]:match("arguments%.lua$") ~= nil, arg[1], arg[2])]]))
assert(file:close())

local command = string.format("lua -E %q alpha beta > %q", script_path, output_path)
t.truth(os.execute(command))
local output = assert(io.open(output_path, "r"))
t.equal(output:read("l"), "true\talpha\tbeta")
t.truth(output:close())

t.truth(os.execute(string.format("lua -E -e 'print(6 * 7)' > %q", output_path)))
output = assert(io.open(output_path, "r"))
t.equal(output:read("l"), "42")
t.truth(output:close())

local initialization = "error('LUA_INIT_5_5 must not run')"
local isolated = string.format(
    "LUA_INIT_5_5=%q lua -E -e 'print(42)' > %q 2> %q",
    initialization,
    output_path,
    error_path
)
t.truth(os.execute(isolated))

local ok, reason, status = os.execute("lua -E -e 'os.exit(7)'")
t.equal(ok, nil)
t.equal(reason, "exit")
t.equal(status, 7)

t.truth(os.remove(script_path))
t.truth(os.remove(output_path))
t.truth(os.remove(error_path))

-- -E 忽略 LUA_INIT_*、LUA_PATH_* 与 LUA_CPATH_*；runner 的精确清理另由 harness 验证。
t.done()
