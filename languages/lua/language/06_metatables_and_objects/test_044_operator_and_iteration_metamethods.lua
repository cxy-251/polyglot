-- polyglot-covers: lua.metatables.operator_and_iteration_protocols

local t = require("support.assertions")
local vector_metatable = {}

local function vector(value)
    return setmetatable({value = value}, vector_metatable)
end
local function scalar(value)
    return type(value) == "table" and value.value or value
end

vector_metatable.__add = function(left, right)
    return vector(scalar(left) + scalar(right))
end
vector_metatable.__unm = function(value)
    return vector(-value.value)
end
vector_metatable.__band = function(left, right)
    return vector(left.value & right.value)
end
vector_metatable.__len = function() return 1 end
vector_metatable.__concat = function(left, right)
    return tostring(left.value) .. right
end
vector_metatable.__pairs = function(self)
    return next, {magnitude = self.value}, nil
end

t.equal((vector(40) + vector(2)).value, 42)
t.equal((2 + vector(40)).value, 42)
t.equal((-vector(7)).value, -7)
t.equal((vector(0x0f) & vector(0x33)).value, 0x03)
t.equal(#vector(42), 1)
t.equal(vector(42) .. "!", "42!")

local copied = {}
for key, item in pairs(vector(42)) do
    copied[key] = item
end
t.equal(copied.magnitude, 42)

t.done()
