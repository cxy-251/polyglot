-- polyglot-covers: lua.expressions.power_unary_and_mixed_numbers

local t = require("support.assertions")

t.equal(2 ^ 3, 8.0)
t.equal(math.type(2 ^ 3), "float")
t.equal(-2 ^ 2, -4.0)
t.equal((-2) ^ 2, 4.0)
t.equal(3 + 0.5, 3.5)
t.equal(math.type(3 + 0.5), "float")
t.equal(6 / 2, 3.0)
t.equal(math.type(6 / 2), "float")

t.done()
