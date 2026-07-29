-- polyglot-covers: lua.patterns.language_iteration_and_substitution

local t = require("support.assertions")

local start_position, end_position = string.find("abc123xyz", "%d+")
t.equal(start_position, 4)
t.equal(end_position, 6)
local name, value = string.match("answer=42", "^(%a+)=(%d+)$")
t.equal(name, "answer")
t.equal(value, "42")
t.equal(string.match("before (a(b)c) after", "%b()"), "(a(b)c)")

local words = {}
for word in string.gmatch("one, two; three", "%f[%a](%a+)%f[%A]") do
    words[#words + 1] = word
end
t.equal(table.concat(words, ","), "one,two,three")

local replaced, count = string.gsub("a1 b2", "(%a)(%d)", "%2%1")
t.equal(replaced, "1a 2b")
t.equal(count, 2)
t.equal(string.gsub("a b", "%a", {a = "A", b = "B"}), "A B")
t.equal(string.gsub("1 2", "%d", function(digit)
    return tostring(tonumber(digit) * 10)
end), "10 20")

-- Lua pattern 不是正则表达式：没有 alternation，却有 frontier 与 balanced item。
t.equal(string.match("100% ready", "100%%"), "100%")
t.equal(string.match("abc", "z"), nil)

t.done()
