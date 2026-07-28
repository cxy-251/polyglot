-- polyglot-covers: lua.tables.key_normalization

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

t.raises(function()
    values[nil] = "invalid"
end, "table index is nil")
t.raises(function()
    values[0 / 0] = "invalid"
end, "table index is NaN")

t.done()
