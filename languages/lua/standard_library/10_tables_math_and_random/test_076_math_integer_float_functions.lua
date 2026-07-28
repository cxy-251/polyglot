-- polyglot-covers: lua.math.integer_and_float_functions

local t = require("support.assertions")

t.equal(math.abs(-42), 42)
t.equal(math.floor(3.75), 3)
t.equal(math.ceil(3.25), 4)
t.equal(math.modf(3.75), 3.0)
local integer_part, fractional_part = math.modf(-3.75)
t.equal(integer_part, -3.0)
t.equal(fractional_part, -0.75)
t.equal(math.fmod(-7, 3), -1)
t.equal(math.sqrt(81), 9.0)
t.near(math.sin(math.pi / 2), 1.0, 1e-15)

t.done()
