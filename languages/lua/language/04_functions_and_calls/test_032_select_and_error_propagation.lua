-- polyglot-covers: lua.functions.select_and_error_propagation

local t = require("support.assertions")

local function inspect(...)
    return select("#", ...), select(2, ...)
end

local count, second, third = inspect("a", nil, "c")
t.equal(count, 3)
t.equal(second, nil)
t.equal(third, "c")

t.pack_equal(table.pack(select(-2, "a", "b", "c")), {n = 2, "b", "c"})
t.raises(function()
    return select(0, "a")
end, "index out of range")

local function caller()
    error({code = 42})
end
local ok, value = pcall(caller)
t.falsey(ok)
t.equal(type(value), "table")
t.equal(value.code, 42)

t.done()
