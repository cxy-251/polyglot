-- polyglot-covers: lua.tables.ipairs_and_mutation_boundaries

local t = require("support.assertions")

local sparse = {"a", "b", nil, "d"}
local visited = {}
for index, value in ipairs(sparse) do
    visited[#visited + 1] = {index, value}
end

t.equal(#visited, 2)
t.equal(visited[1][1], 1)
t.equal(visited[2][2], "b")

local values = {1, 2, 3}
for index, value in ipairs(values) do
    values[index] = value * 10
end
t.equal(values[1], 10)
t.equal(values[3], 30)

-- 遍历期间更新现有字段可观察；新增尚未存在的键会使遍历边界依赖具体操作，应避免。
t.done()
