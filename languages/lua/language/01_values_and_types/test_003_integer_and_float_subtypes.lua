-- polyglot-covers: lua.values.integer_and_float_subtypes

local t = require("support.assertions")

t.equal(type(3), "number")
t.equal(type(3.0), "number")
t.equal(math.type(3), "integer")
t.equal(math.type(3.0), "float")
t.same(3, 3.0)
t.equal(math.tointeger(3.0), 3)
t.equal(math.tointeger(3.25), nil)
t.equal(0x1p2, 4.0)

t.done()
