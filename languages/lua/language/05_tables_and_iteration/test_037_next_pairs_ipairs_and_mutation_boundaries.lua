-- polyglot-covers: lua.tables.iteration_protocols_and_mutation

local t = require("support.assertions")

local source = {alpha = 1, beta = 2, gamma = 3}
local observed = {}
for key, value in pairs(source) do
    observed[key] = value
end
t.equal(observed.alpha, 1)
t.equal(observed.beta, 2)
t.equal(observed.gamma, 3)

local count = 0
for _ in next, source do
    count = count + 1
end
t.equal(count, 3)

-- pairs/next 的顺序未指定；ipairs 只走从 1 开始、遇到第一个 nil 结束的整数前缀。
local sparse = {"a", "b", nil, "d"}
local visited = {}
for index, value in ipairs(sparse) do
    visited[#visited + 1] = {index, value}
end
t.equal(#visited, 2)
t.equal(visited[2][2], "b")

-- 更新当前已存在字段是可观察的；新增键或移除尚未访问的键会使 next 行为未指定。
local values = {1, 2, 3}
for index, value in ipairs(values) do
    values[index] = value * 10
end
t.equal(table.concat(values, ","), "10,20,30")

t.done()
