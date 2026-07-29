-- polyglot-covers: lua.expressions.arithmetic_subtypes_and_coercion

local t = require("support.assertions")

t.equal(7 + 5, 12)
t.equal(-7 // 3, -3)
t.equal(-7 % 3, 2)
t.equal(7 % -3, -2)
t.equal(7.5 // 2, 3.0)
t.equal(math.type(7.5 // 2), "float")

-- / 与 ^ 总产生 float；混合算术在需要时把 integer 转为 float。
t.equal(6 / 2, 3.0)
t.equal(math.type(6 / 2), "float")
t.equal(2 ^ 3, 8.0)
t.equal(math.type(2 ^ 3), "float")
t.equal(3 + 0.5, 3.5)

-- tonumber 是显式解析入口；算术和拼接也有各自受限的隐式转换。
t.equal(tonumber("2a", 16), 42)
t.equal(tonumber(" 3.5 "), 3.5)
t.equal(tonumber("not a number"), nil)
t.equal("6" + 7, 13)
t.equal(12 .. 3, "123")
t.raises(function() return "six" + 7 end)

t.done()
