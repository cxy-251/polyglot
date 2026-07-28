-- polyglot-covers: lua.tables.sequences_borders_and_length

local t = require("support.assertions")

local sequence = {"a", "b", "c"}
t.equal(#sequence, 3)
t.equal(sequence[#sequence], "c")

local sparse = {[1] = "a", [3] = "c", [8] = "h"}
local border = #sparse
t.truth(border >= 0)
t.truth((border == 0 or sparse[border] ~= nil) and sparse[border + 1] == nil)

-- 稀疏表可能有多个 border；语言只保证长度运算返回其中一个合法 border。
t.truth(border == 1 or border == 3 or border == 8)

local empty = {}
t.equal(#empty, 0)

t.done()
