-- polyglot-covers: lua.patterns.captures

local t = require("support.assertions")

local start_position, end_position = string.find("abc123xyz", "%d+")
t.equal(start_position, 4)
t.equal(end_position, 6)

local name, value = string.match("answer=42", "^(%a+)=(%d+)$")
t.equal(name, "answer")
t.equal(value, "42")

local balanced = string.match("before (a(b)c) after", "%b()")
t.equal(balanced, "(a(b)c)")
t.equal(string.match("abc", "^a.-c$"), "abc")
t.equal(string.match("abc", "z"), nil)

-- Lua pattern 是独立的小型模式语言，不提供通用正则表达式的 alternation 等语义。
t.done()
