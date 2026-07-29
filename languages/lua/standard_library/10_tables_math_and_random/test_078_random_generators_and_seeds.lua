-- polyglot-covers: lua.math.random_generators_and_seeds

local t = require("support.assertions")

math.randomseed(12345, 67890)
local first = {
    math.random(),
    math.random(10),
    math.random(-5, 5),
}

math.randomseed(12345, 67890)
t.equal(math.random(), first[1])
t.equal(math.random(10), first[2])
t.equal(math.random(-5, 5), first[3])

for _ = 1, 20 do
    local value = math.random(3, 7)
    t.truth(value >= 3 and value <= 7)
end

-- 每个课程文件使用独立进程，RNG 状态随进程销毁，不污染后续测试。
-- 固定双 seed 只承诺在同一 Lua 实现中重放序列；具体输出值不作为课程断言。
t.done()
