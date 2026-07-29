-- polyglot-covers: lua.math.subtypes_rounding_conversion_and_transcendentals

local t = require("support.assertions")

t.equal(math.abs(-42), 42)
t.equal(math.floor(3.75), 3)
t.equal(math.type(math.floor(3.75)), "integer")
t.equal(math.ceil(-3.5), -3)
local integer_part, fractional_part = math.modf(-3.75)
t.equal(integer_part, -3.0)
t.equal(fractional_part, -0.75)
t.equal(math.fmod(-7, 3), -1)

t.equal(math.tointeger("42"), 42)
t.equal(math.tointeger("42.5"), nil)
t.equal(math.tointeger(math.huge), nil)
t.truth(math.ult(1, -1))
t.falsey(math.ult(-1, 1))

t.equal(math.min(4, -2, 7), -2)
t.equal(math.max(4, -2, 7), 7)
t.near(math.sqrt(81), 9, 0)
t.near(math.sin(math.pi / 2), 1, 1e-15)
t.near(math.log(8, 2), 3, 1e-12)
t.near(math.deg(math.pi), 180, 1e-12)

-- maxinteger/mininteger 暴露当前构建范围；课程不把标准 Lua 的常见 64 位配置写成普遍保证。
t.truth(math.mininteger < 0)
t.truth(math.maxinteger > 0)

t.done()
