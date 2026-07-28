-- polyglot-covers: lua.functions.parentheses_and_return_adjustment

local t = require("support.assertions")

local function pair()
    return 10, 20
end

local function preserved()
    return pair()
end

local function truncated()
    return (pair())
end

t.pack_equal(table.pack(preserved()), {n = 2, 10, 20})
t.pack_equal(table.pack(truncated()), {n = 1, 10})
t.pack_equal(table.pack((pair())), {n = 1, 10})

local only_first = (pair())
t.equal(only_first, 10)

t.done()
