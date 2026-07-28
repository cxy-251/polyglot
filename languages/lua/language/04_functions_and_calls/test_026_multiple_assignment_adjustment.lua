-- polyglot-covers: lua.functions.multiple_assignment_adjustment

local t = require("support.assertions")

local function values()
    return "a", nil, "c"
end

local first, second, third, fourth = values()
t.equal(first, "a")
t.equal(second, nil)
t.equal(third, "c")
t.equal(fourth, nil)

local left, right = 1, 2
left, right = right, left
t.equal(left, 2)
t.equal(right, 1)

local list = {10, 20}
local index = 1
index, list[index] = 2, 99
t.equal(index, 2)
t.equal(list[1], 99)

t.done()
