-- polyglot-covers: lua.debug.metatable_bypass

local t = require("support.assertions")
local hidden = {__metatable = "sealed", answer = 42}
local value = setmetatable({}, hidden)

t.equal(getmetatable(value), "sealed")
t.same(debug.getmetatable(value), hidden)

local replacement = {__index = {answer = 43}}
t.same(debug.setmetatable(value, replacement), value)
t.same(getmetatable(value), replacement)
t.equal(value.answer, 43)

debug.setmetatable(value, hidden)
t.equal(getmetatable(value), "sealed")

t.done()
