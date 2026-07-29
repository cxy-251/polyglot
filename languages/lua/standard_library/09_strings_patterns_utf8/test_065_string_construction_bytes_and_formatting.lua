-- polyglot-covers: lua.strings.construction_bytes_and_formatting

local t = require("support.assertions")

local original = "Lua"
t.equal(string.upper(original), "LUA")
t.equal(original, "Lua")
t.equal(string.sub(original, 2, 3), "ua")
t.equal(string.rep("ab", 3, "-"), "ab-ab-ab")

local binary = string.char(0, 127, 128, 255)
t.equal(#binary, 4)
t.pack_equal(table.pack(string.byte(binary, 1, 4)), {n = 4, 0, 127, 128, 255})

t.equal("\x41\u{42}", "AB")
t.equal("a\z    b", "ab")
local long = [=[
first
[[nested delimiters]]
last
]=]
t.equal(long, "first\n[[nested delimiters]]\nlast\n")

t.equal(string.format("%04d", 42), "0042")
t.equal(string.format("%.2f", 1.25), "1.25")
local quoted = string.format("%q", "a\nb")
t.equal(assert(load("return " .. quoted, "quoted", "t"))(), "a\nb")

t.done()
