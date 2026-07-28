-- polyglot-covers: lua.expressions.numeric_conversion

local t = require("support.assertions")

t.equal(tonumber("42"), 42)
t.equal(tonumber("2a", 16), 42)
t.equal(tonumber(" 3.5 "), 3.5)
t.equal(tonumber("not a number"), nil)
t.equal("6" + 7, 13)
t.equal("6" * "7", 42)
t.equal(12 .. 3, "123")
t.raises(function()
    return "six" + 7
end, "attempt to add")

t.done()
