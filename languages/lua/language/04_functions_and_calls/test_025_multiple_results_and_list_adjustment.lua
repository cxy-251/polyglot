-- polyglot-covers: lua.functions.multiple_results_and_adjustment

local t = require("support.assertions")

local function values()
    return "a", nil, "c"
end
local function capture(...)
    return table.pack(...)
end
local function fixed(first, second)
    return first, second
end

-- 参数和赋值按目标数量补 nil 或截断；最后一个函数调用可以展开全部结果。
t.pack_equal(capture(values()), {n = 3, "a", nil, "c"})
t.pack_equal(capture(values(), "tail"), {n = 2, "a", "tail"})
t.pack_equal(capture("head", values()), {n = 4, "head", "a", nil, "c"})
t.pack_equal(table.pack(fixed(values())), {n = 2, "a", nil})

local first, second, third, fourth = values()
t.equal(first, "a")
t.equal(second, nil)
t.equal(third, "c")
t.equal(fourth, nil)

local left, right = 1, 2
left, right = right, left
t.equal(left, 2)
t.equal(right, 1)

-- 括号把多结果调用调整为一个结果；table constructor 仅展开最后一个 list field。
local function preserved() return values() end
local function truncated() return (values()) end
t.pack_equal(table.pack(preserved()), {n = 3, "a", nil, "c"})
t.pack_equal(table.pack(truncated()), {n = 1, "a"})
local constructed = {values(), "tail"}
t.equal(constructed[1], "a")
t.equal(constructed[2], "tail")

t.done()
