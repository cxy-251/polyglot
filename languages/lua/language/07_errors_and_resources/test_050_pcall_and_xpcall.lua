-- polyglot-covers: lua.errors.protected_calls

local t = require("support.assertions")

local ok, left, right = pcall(function(first, second)
    return first + second, first * second
end, 6, 7)
t.truth(ok)
t.equal(left, 13)
t.equal(right, 42)

local handled, transformed = xpcall(function()
    error("original")
end, function(error_value)
    return {kind = "handled", original = error_value}
end)
t.falsey(handled)
t.equal(transformed.kind, "handled")
t.matches(transformed.original, "original")

t.done()
