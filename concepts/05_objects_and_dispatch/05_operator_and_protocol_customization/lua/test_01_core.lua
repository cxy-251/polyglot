-- Common question: which operators and protocols can user values customize?
-- Inputs: arithmetic, equality, length, call, string conversion, and iteration.
-- Observations: metamethod dispatch, raw bypass, returned values, and protocol-specific hooks.
-- polyglot-family: objects_and_dispatch
-- polyglot-concept: operator_and_protocol_customization
-- polyglot-related: languages/lua/language/06_metatables_and_objects/test_044_arithmetic_and_bitwise_metamethods.lua

local t = require("support.assertions")
local metatable = {}
metatable.__add = function(left, right) return setmetatable({value = left.value + right.value}, metatable) end
metatable.__eq = function(left, right) return left.value == right.value end
metatable.__len = function(value) return value.value end
metatable.__call = function(value, increment) return value.value + increment end
metatable.__tostring = function(value) return "Value(" .. value.value .. ")" end

local left = setmetatable({value = 40}, metatable)
local right = setmetatable({value = 2}, metatable)
t.equal((left + right).value, 42)
t.truth(left == setmetatable({value = 40}, metatable))
t.falsey(rawequal(left, setmetatable({value = 40}, metatable)))
t.equal(#left, 40)
t.equal(left(2), 42)
t.equal(tostring(right), "Value(2)")

t.done()
