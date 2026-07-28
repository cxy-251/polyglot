-- polyglot-covers: lua.patterns.frontier_and_balanced

local t = require("support.assertions")

local words = {}
for word in string.gmatch("one, two; three", "%f[%a](%a+)%f[%A]") do
    words[#words + 1] = word
end
t.equal(#words, 3)
t.equal(words[1], "one")
t.equal(words[2], "two")
t.equal(words[3], "three")

local nested = "call(a, nested(b), c)"
t.equal(string.match(nested, "%b()"), "(a, nested(b), c)")

local escaped = string.match("100% ready", "100%%")
t.equal(escaped, "100%")

t.done()
