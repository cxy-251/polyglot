-- polyglot-covers: lua.table_library.concat_and_ranges

local t = require("support.assertions")
local values = {"zero", "one", "two", "three"}

t.equal(table.concat(values, "|"), "zero|one|two|three")
t.equal(table.concat(values, ",", 2, 3), "one,two")
t.equal(table.concat(values, "", 4, 3), "")

local packed = table.pack("a", nil, "c")
t.equal(packed.n, 3)
t.pack_equal(table.pack(table.unpack(packed, 1, packed.n)), packed)

t.raises(function()
    return table.concat({"a", {}}, ",")
end, "invalid value")

t.done()
