-- polyglot-covers: lua.expressions.arithmetic_floor_division_and_modulo

local t = require("support.assertions")

t.equal(7 + 5, 12)
t.equal(7 - 5, 2)
t.equal(7 * 5, 35)
t.equal(7 // 3, 2)
t.equal(-7 // 3, -3)
t.equal(-7 % 3, 2)
t.equal(7 % -3, -2)
t.equal(7.5 // 2, 3.0)
t.equal(math.type(7.5 // 2), "float")

t.done()
