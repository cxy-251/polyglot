-- polyglot-covers: lua.debug.function_information

local t = require("support.assertions")

local function sample(first, second, ...)
    return first + second
end

local info = debug.getinfo(sample, "Snu")
t.equal(info.what, "Lua")
t.equal(info.namewhat, "")
t.equal(info.nparams, 2)
t.truth(info.isvararg)
t.equal(type(info.linedefined), "number")
t.equal(type(info.lastlinedefined), "number")
t.matches(info.short_src, "test_089")

local c_info = debug.getinfo(math.abs, "S")
t.equal(c_info.what, "C")

t.done()
