-- polyglot-covers: lua.values.truthiness_and_absence

local t = require("support.assertions")

local representatives = {
    {"boolean", false},
    {"number", 7},
    {"string", "lua"},
    {"function", function() end},
    {"table", {}},
    {"thread", coroutine.create(function() end)},
}
for _, representative in ipairs(representatives) do
    t.equal(type(representative[2]), representative[1])
end
t.equal(type(nil), "nil")

-- 只有 false 与 nil 是假值；0、空串和空表都进入真分支。
t.falsey(false)
t.falsey(nil)
t.truth(0)
t.truth("")
t.truth({})
t.equal(0 and "selected", "selected")
t.equal(nil or "fallback", "fallback")

-- nil 也表示 table 中没有该键；false 则是能够保存和遍历的普通值。
local values = {present = false}
t.equal(values.present, false)
t.equal(values.absent, nil)
values.present = nil
t.equal(next(values), nil)

t.done()
