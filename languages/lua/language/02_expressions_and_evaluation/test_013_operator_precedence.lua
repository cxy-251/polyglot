-- polyglot-covers: lua.expressions.operator_precedence

local t = require("support.assertions")

t.equal(2 + 3 * 4, 14)
t.equal((2 + 3) * 4, 20)
t.equal(2 ^ 3 ^ 2, 512.0)
t.equal("a" .. "b" .. "c", "abc")
t.truth(not false and true)
t.equal(1 | 2 & 4, 1)
t.equal(1 << 2 + 1, 8)

-- 拼接和幂都是右结合；括号用于把迁移意图写清楚。
t.equal(("a" .. "b") .. "c", "abc")

t.done()
