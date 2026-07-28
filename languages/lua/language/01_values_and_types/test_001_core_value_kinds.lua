-- polyglot-covers: lua.values.core_value_kinds

local t = require("support.assertions")

t.equal(type(nil), "nil")
t.equal(type(false), "boolean")
t.equal(type(7), "number")
t.equal(type("lua"), "string")
t.equal(type(function() end), "function")
t.equal(type({}), "table")
t.equal(type(coroutine.create(function() end)), "thread")

local native = require("polyglot_native")
t.equal(native.add(20, 22), 42)

local command = string.format("%q state", assert(os.getenv("POLYGLOT_LUA_C_API_HOST")))
local pipe = assert(io.popen(command, "r"))
local output = pipe:read("a")
local ok, reason, status = pipe:close()
t.truth(ok, string.format("host failed: %s %s", tostring(reason), tostring(status)))
t.matches(output, "C API case passed: state")

t.done()
