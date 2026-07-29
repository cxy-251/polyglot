-- Common question: how does sequence mutation affect indices and active traversal?
-- Inputs: insertion, removal, saved numeric indices, and in-place value updates.
-- Observations: shifting positions, stale indices, fixed-range mutation, and sequence borders.
-- polyglot-family: collections_and_iteration
-- polyglot-concept: sequence_mutation_and_invalidation
-- polyglot-related: languages/lua/standard_library/10_tables_math_and_random/
-- polyglot-related+: test_073_table_sequence_mutation_packing_and_capacity_hints.lua

local t = require("support.assertions")
local values = {"a", "b", "c"}
local saved_index = 2

table.insert(values, 1, "new")
t.equal(values[saved_index], "a")
t.equal(values[3], "b")

t.equal(table.remove(values, 1), "new")
t.equal(values[saved_index], "b")

for index = 1, #values do
    values[index] = values[index]:upper()
end
t.equal(table.concat(values), "ABC")

-- next/pairs 遍历期间新增字段的访问顺序未指定；结构变化应与遍历分离。
t.done()
