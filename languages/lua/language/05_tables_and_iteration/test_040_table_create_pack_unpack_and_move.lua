-- polyglot-covers: lua.tables.create_pack_unpack_and_move

local t = require("support.assertions")

local created = table.create(4, 2)
t.equal(type(created), "table")
t.equal(next(created), nil)

local packed = table.pack("a", nil, "c")
t.equal(packed.n, 3)
t.equal(packed[1], "a")
t.equal(packed[2], nil)
t.equal(packed[3], "c")
t.pack_equal(table.pack(table.unpack(packed, 1, packed.n)), packed)

local values = {1, 2, 3, 4}
table.move(values, 1, 3, 2)
t.equal(values[1], 1)
t.equal(values[2], 1)
t.equal(values[3], 2)
t.equal(values[4], 3)

t.done()
