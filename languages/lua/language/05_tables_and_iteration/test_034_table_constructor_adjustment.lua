-- polyglot-covers: lua.tables.constructor_adjustment

local t = require("support.assertions")

local function triple()
    return "a", "b", "c"
end

local final_multires = {"head", triple()}
t.equal(#final_multires, 4)
t.equal(final_multires[1], "head")
t.equal(final_multires[2], "a")
t.equal(final_multires[4], "c")

local nonfinal_multires = {triple(), tail = "named"}
t.equal(#nonfinal_multires, 1)
t.equal(nonfinal_multires[1], "a")
t.equal(nonfinal_multires.tail, "named")

local explicit_fields = {[1] = triple(), [2] = "second"}
t.equal(explicit_fields[1], "a")
t.equal(explicit_fields[2], "second")

t.done()
