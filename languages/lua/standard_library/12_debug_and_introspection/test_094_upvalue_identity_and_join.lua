-- polyglot-covers: lua.debug.upvalue_identity_and_join

local t = require("support.assertions")

local function make(value)
    return function()
        return value
    end
end

local first = make("first")
local second = make("second")
t.equal(first(), "first")
t.equal(second(), "second")
t.falsey(debug.upvalueid(first, 1) == debug.upvalueid(second, 1))

debug.upvaluejoin(second, 1, first, 1)
t.equal(second(), "first")
t.truth(debug.upvalueid(first, 1) == debug.upvalueid(second, 1))

local name = debug.setupvalue(first, 1, "joined")
t.equal(name, "value")
t.equal(first(), "joined")
t.equal(second(), "joined")

t.done()
