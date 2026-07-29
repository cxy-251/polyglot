-- polyglot-covers: lua.values.number_subtypes_and_boundaries

local t = require("support.assertions")

-- integer 与 float 同属 number，但 math.type 暴露实际数值子类型。
t.equal(type(3), "number")
t.equal(type(3.0), "number")
t.equal(math.type(3), "integer")
t.equal(math.type(3.0), "float")
t.truth(3 == 3.0)
t.equal(math.tointeger(3.0), 3)
t.equal(math.tointeger(3.25), nil)

-- 整数宽度由构建配置决定；语言保证溢出按该宽度取模，不应锁定 64 位常量。
t.equal(math.maxinteger + 1, math.mininteger)
t.equal(math.mininteger - 1, math.maxinteger)
t.equal(-math.mininteger, math.mininteger)
t.equal(math.tointeger(tostring(math.maxinteger)), math.maxinteger)
t.equal(math.tointeger(1e100), nil)

local infinity = math.huge
local nan = 0.0 / 0.0
t.truth(infinity > math.maxinteger)
t.equal(1 / infinity, 0.0)
t.falsey(nan == nan)
t.truth(nan ~= nan)
t.equal(math.type(infinity), "float")
t.equal(math.type(nan), "float")

t.done()
