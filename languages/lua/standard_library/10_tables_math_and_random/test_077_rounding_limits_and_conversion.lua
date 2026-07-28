-- polyglot-covers: lua.math.rounding_limits_and_conversion

local t = require("support.assertions")

t.equal(math.floor(3), 3)
t.equal(math.type(math.floor(3.5)), "integer")
t.equal(math.ceil(-3.5), -3)
t.equal(math.maxinteger, 0x7fffffffffffffff)
t.equal(math.mininteger, -0x7fffffffffffffff - 1)
t.equal(math.tointeger("42"), 42)
t.equal(math.tointeger("42.5"), nil)
t.equal(math.tointeger(math.huge), nil)
t.truth(math.ult(1, -1))
t.falsey(math.ult(-1, 1))

t.done()
