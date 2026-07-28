-- polyglot-covers: lua.values.integer_range_and_overflow

local t = require("support.assertions")

t.equal(math.maxinteger + 1, math.mininteger)
t.equal(math.mininteger - 1, math.maxinteger)
t.equal(-math.mininteger, math.mininteger)
t.equal(math.maxinteger // 2, 4611686018427387903)
t.equal(math.tointeger(tostring(math.maxinteger)), math.maxinteger)
t.equal(math.tointeger(1e100), nil)

-- 整数算术按二进制补码取模；具体 64 位宽由当前锁定构建通过配置测试确认。
t.equal(string.packsize("j"), 8)

t.done()
