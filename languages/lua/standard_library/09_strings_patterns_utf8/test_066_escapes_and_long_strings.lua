-- polyglot-covers: lua.strings.escapes_and_long_strings

local t = require("support.assertions")

t.equal("\x41\u{42}", "AB")
t.equal("line\nbreak", "line" .. string.char(10) .. "break")
t.equal("a\z    b", "ab")

local long = [=[
first
[[nested delimiters]]
last
]=]
t.equal(long, "first\n[[nested delimiters]]\nlast\n")

local escaped_quote = "Lua says \"hello\""
t.equal(escaped_quote, [[Lua says "hello"]])

t.done()
