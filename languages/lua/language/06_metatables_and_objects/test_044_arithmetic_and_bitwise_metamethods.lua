-- polyglot-covers: lua.metatables.arithmetic_and_bitwise_metamethods

local t = require("support.assertions")
local vector_metatable = {}

local function vector(value)
    return setmetatable({value = value}, vector_metatable)
end

vector_metatable.__add = function(left, right)
    local left_value = type(left) == "table" and left.value or left
    local right_value = type(right) == "table" and right.value or right
    return vector(left_value + right_value)
end
vector_metatable.__unm = function(value)
    return vector(-value.value)
end
vector_metatable.__band = function(left, right)
    return vector(left.value & right.value)
end

t.equal((vector(40) + vector(2)).value, 42)
t.equal((2 + vector(40)).value, 42)
t.equal((-vector(7)).value, -7)
t.equal((vector(0x0f) & vector(0x33)).value, 0x03)

t.done()
