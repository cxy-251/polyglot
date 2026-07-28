-- polyglot-covers: lua.errors.levels_and_tracebacks

local t = require("support.assertions")

local function public_api()
    error("bad input", 2)
end

local function caller()
    public_api()
end

local ok, traceback = xpcall(caller, function(error_value)
    return debug.traceback(error_value, 2)
end)
t.falsey(ok)
t.matches(traceback, "bad input")
t.matches(traceback, "public_api")
t.matches(traceback, "stack traceback")

local raw_ok, raw_error = pcall(function()
    error({code = 42}, 0)
end)
t.falsey(raw_ok)
t.equal(raw_error.code, 42)

t.done()
