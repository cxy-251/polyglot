-- polyglot-covers: lua.patterns.gmatch_and_gsub

local t = require("support.assertions")

local entries = {}
for key, value in string.gmatch("a=1;b=2", "(%a)=(%d)") do
    entries[key] = tonumber(value)
end
t.equal(entries.a, 1)
t.equal(entries.b, 2)

local replaced, count = string.gsub("a1 b2", "(%a)(%d)", "%2%1")
t.equal(replaced, "1a 2b")
t.equal(count, 2)

local mapped = string.gsub("a b", "%a", {a = "A", b = "B"})
t.equal(mapped, "A B")

local called = string.gsub("1 2", "%d", function(value)
    return tostring(tonumber(value) * 10)
end)
t.equal(called, "10 20")

t.done()
