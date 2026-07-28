-- polyglot-covers: lua.strings.immutability_and_bytes

local t = require("support.assertions")

local original = "Lua"
local upper = string.upper(original)
t.equal(original, "Lua")
t.equal(upper, "LUA")
t.equal(string.sub(original, 2, 3), "ua")
t.equal(string.rep("ab", 3, "-"), "ab-ab-ab")

local binary = string.char(0, 127, 128, 255)
t.equal(#binary, 4)
t.pack_equal(table.pack(string.byte(binary, 1, 4)), {n = 4, 0, 127, 128, 255})

t.done()
