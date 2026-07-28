-- polyglot-covers: lua.functions.local_recursion_and_tail_calls

local t = require("support.assertions")

local factorial
factorial = function(value)
    if value == 0 then
        return 1
    end
    return value * factorial(value - 1)
end

t.equal(factorial(6), 720)

local function countdown(value)
    if value == 0 then
        return "done"
    end
    return countdown(value - 1)
end

-- 尾位置调用由语言保证复用控制状态；测试结果而不锁定调试栈文本。
t.equal(countdown(100000), "done")

t.done()
