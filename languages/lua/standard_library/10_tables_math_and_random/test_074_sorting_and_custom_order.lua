-- polyglot-covers: lua.table_library.sorting_and_custom_order

local t = require("support.assertions")

local numbers = {4, 1, 3, 2}
table.sort(numbers)
t.equal(table.concat(numbers, ","), "1,2,3,4")

local records = {
    {name = "beta", rank = 2},
    {name = "alpha", rank = 1},
    {name = "gamma", rank = 2},
}
table.sort(records, function(left, right)
    if left.rank ~= right.rank then
        return left.rank < right.rank
    end
    return left.name < right.name
end)
t.equal(records[1].name, "alpha")
t.equal(records[2].name, "beta")
t.equal(records[3].name, "gamma")

-- table.sort 不保证稳定；需要稳定结果时把原位置纳入比较键。
t.done()
