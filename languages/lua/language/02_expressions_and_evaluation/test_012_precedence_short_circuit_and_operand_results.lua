-- polyglot-covers: lua.expressions.precedence_short_circuit_and_results

local t = require("support.assertions")
local calls = 0
local function mark(value)
    calls = calls + 1
    return value
end

-- and/or 短路且返回原操作数，不把结果强制转成 boolean。
t.equal(false and mark("unused"), false)
t.equal("left" or mark("unused"), "left")
t.equal(calls, 0)
t.equal(true and mark("right"), "right")
t.equal(false or mark("fallback"), "fallback")
t.equal(calls, 2)
t.equal(0 or "unused", 0)

-- 幂和拼接右结合；幂高于一元负号，移位低于算术。
t.equal(2 + 3 * 4, 14)
t.equal(2 ^ 3 ^ 2, 512.0)
t.equal(-2 ^ 2, -4.0)
t.equal((-2) ^ 2, 4.0)
t.equal(1 << 2 + 1, 8)
t.equal("a" .. "b" .. "c", "abc")
t.equal(#"Lua\0", 4)

t.done()
