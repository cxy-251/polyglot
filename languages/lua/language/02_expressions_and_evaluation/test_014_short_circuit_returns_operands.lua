-- polyglot-covers: lua.expressions.short_circuit_returns_operands

local t = require("support.assertions")
local calls = 0

local function mark(value)
    calls = calls + 1
    return value
end

t.equal(false and mark("unused"), false)
t.equal(nil and mark("unused"), nil)
t.equal("left" or mark("unused"), "left")
t.equal(calls, 0)
t.equal(true and mark("right"), "right")
t.equal(false or mark("fallback"), "fallback")
t.equal(calls, 2)
t.equal(0 or "fallback", 0)

t.done()
