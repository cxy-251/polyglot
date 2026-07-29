-- polyglot-covers: lua.errors.values_protected_calls_and_context

local t = require("support.assertions")

local marker = {kind = "parse", input = "bad"}
local ok, value = pcall(function() error(marker) end)
t.falsey(ok)
t.same(value, marker)

local call_ok, sum, product = pcall(function(left, right)
    return left + right, left * right
end, 6, 7)
t.truth(call_ok)
t.equal(sum, 13)
t.equal(product, 42)

local handled, transformed = xpcall(function()
    error("original")
end, function(error_value)
    return {
        kind = "handled",
        original = error_value,
        traceback = debug.traceback(nil, 2),
    }
end)
t.falsey(handled)
t.equal(transformed.kind, "handled")
t.matches(transformed.original, "original")
t.matches(transformed.traceback, "stack traceback")

local first, second = assert("value", "extra")
t.equal(first, "value")
t.equal(second, "extra")
t.same(select(2, pcall(assert, false, marker)), marker)

-- Lua 没有内建 exception class 或 cause；应用可用任意非 nil 值显式表达上下文。
local outer = {kind = "load", cause = marker}
ok, value = pcall(function() error(outer, 0) end)
t.falsey(ok)
t.same(value, outer)
t.equal(value.cause.kind, "parse")

t.done()
