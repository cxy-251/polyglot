-- polyglot-covers: lua.tables.keys_constructors_and_absence

local t = require("support.assertions")

local values = {}
values[1] = "integer"
t.equal(values[1.0], "integer")
values[1.0] = "normalized"
t.equal(values[1], "normalized")
values["1"] = "string"
t.equal(values[1], "normalized")
t.equal(values["1"], "string")

local object_key = {}
values[object_key] = "identity"
t.equal(values[object_key], "identity")
t.equal(values[{}], nil)
t.raises(function() values[nil] = "invalid" end)
t.raises(function() values[0 / 0] = "invalid" end)

local function triple()
    return "a", "b", "c"
end
local final_multires = {"head", triple()}
t.equal(final_multires[1], "head")
t.equal(final_multires[2], "a")
t.equal(final_multires[4], "c")

-- 只有 constructor 的最后一个 list field 展开多结果；record field 总调整为一个值。
local nonfinal = {triple(), tail = triple()}
t.equal(nonfinal[1], "a")
t.equal(nonfinal.tail, "a")

t.done()
