-- polyglot-covers: lua.metatables.equality_and_order_metamethods

local t = require("support.assertions")
local metatable = {}

metatable.__eq = function(left, right)
    return left.key == right.key
end
metatable.__lt = function(left, right)
    return left.key < right.key
end
metatable.__le = function(left, right)
    return left.key <= right.key
end

local first = setmetatable({key = 1}, metatable)
local equivalent = setmetatable({key = 1}, metatable)
local later = setmetatable({key = 2}, metatable)

t.truth(first == equivalent)
t.falsey(rawequal(first, equivalent))
t.truth(first < later)
t.truth(first <= equivalent)
t.truth(later > first)
t.truth(later >= equivalent)

t.done()
