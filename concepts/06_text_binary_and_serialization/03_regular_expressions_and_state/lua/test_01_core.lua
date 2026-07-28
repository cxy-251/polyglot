-- Common question: what pattern language is available, and where is match state stored?
-- Inputs: classes, repetition, captures, balanced text, and repeated iteration.
-- Observations: Lua-pattern syntax, returned captures, stateless calls, and gmatch iterator state.
-- polyglot-family: text_binary_and_serialization
-- polyglot-concept: regular_expressions_and_state
-- polyglot-related: languages/lua/standard_library/09_strings_patterns_utf8/test_067_patterns_and_captures.lua

local t = require("support.assertions")

local key, value = string.match("answer=42", "^(%a+)=(%d+)$")
t.equal(key, "answer")
t.equal(value, "42")
t.equal(string.match("call(a(b)c)", "%b()"), "(a(b)c)")

local matches = {}
for word in string.gmatch("one two", "%a+") do
    matches[#matches + 1] = word
end
t.equal(table.concat(matches, ","), "one,two")
t.equal(string.match("abc", "%d+"), nil)

-- Lua pattern 不是 regex：没有 alternation、lookaround 或独立 compiled pattern 对象。
t.done()
