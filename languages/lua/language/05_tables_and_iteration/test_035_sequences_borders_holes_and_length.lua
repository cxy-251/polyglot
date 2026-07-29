-- polyglot-covers: lua.tables.sequences_borders_holes_and_length

local t = require("support.assertions")

local sequence = {"a", "b", "c"}
t.equal(#sequence, 3)
t.equal(rawlen(sequence), 3)

local sparse = {[1] = "a", [3] = "c", [8] = "h"}
local border = #sparse
t.truth((border == 0 or sparse[border] ~= nil) and sparse[border + 1] == nil)

-- 有洞的 table 可能存在多个 border，# 只保证返回其中一个；它不是元素计数。
t.truth(border == 1 or border == 3 or border == 8)

local overridden = setmetatable({10, 20, 30}, {
    __len = function() return 99 end,
})
t.equal(#overridden, 99)
t.equal(rawlen(overridden), 3)
overridden[2] = nil
border = rawlen(overridden)
t.truth((border == 0 or overridden[border] ~= nil) and overridden[border + 1] == nil)
t.equal(rawlen("a\0b"), 3)

t.done()
