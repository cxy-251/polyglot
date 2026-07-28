-- Common question: is sorting stable, and how is a custom order defined?
-- Inputs: equal primary keys, original positions, ascending and descending fields.
-- Observations: comparator protocol, explicit tie-breakers, in-place mutation, and stability boundary.
-- polyglot-family: collections_and_iteration
-- polyglot-concept: sorting_stability_and_custom_order
-- polyglot-related: languages/lua/standard_library/10_tables_math_and_random/test_074_sorting_and_custom_order.lua

local t = require("support.assertions")
local values = {
    {group = 2, name = "b", position = 1},
    {group = 1, name = "a", position = 2},
    {group = 2, name = "a", position = 3},
}

table.sort(values, function(left, right)
    if left.group ~= right.group then return left.group < right.group end
    return left.position < right.position
end)
t.equal(values[1].name, "a")
t.equal(values[2].name, "b")
t.equal(values[3].name, "a")

table.sort(values, function(left, right) return left.name > right.name end)
t.equal(values[1].name, "b")

-- table.sort 原地排序且不保证稳定；稳定需求必须把原位置加入比较键。
t.done()
