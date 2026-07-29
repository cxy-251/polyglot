-- Common question: how do key/comparator failures and invalid contracts surface?
-- Inputs: missing fields, comparator errors, mixed incomparable values, and side effects.
-- Observations: immediate propagation, partial mutation allowance, strict-order responsibility, and no key callback.
-- polyglot-family: collections_and_iteration
-- polyglot-concept: sorting_stability_and_custom_order
-- polyglot-related: languages/lua/standard_library/10_tables_math_and_random/test_074_sorting_and_custom_order.lua

local t = require("support.assertions")

local values = {{rank = 2}, {}, {rank = 1}}
t.raises(function()
    table.sort(values, function(left, right)
        assert(left.rank and right.rank, "missing rank")
        return left.rank < right.rank
    end)
end, "missing rank")

t.raises(function()
    table.sort({1, "2"})
end)

local comparisons = 0
table.sort({3, 2, 1}, function(left, right)
    comparisons = comparisons + 1
    return left < right
end)
t.truth(comparisons > 0)

-- Lua 只接受 comparator，没有独立 key function；比较器必须实现一致的严格顺序。
t.done()
