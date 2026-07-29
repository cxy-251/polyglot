-- polyglot-covers: lua.functions.named_varargs_and_select

local t = require("support.assertions")

local function inspect(first, ... rest)
    t.equal(first, "head")
    t.equal(rest.n, 3)
    t.equal(rest[1], "tail")
    t.equal(rest[2], nil)
    t.equal(rest[3], 42)
    return select("#", ...), select(2, ...)
end

local count, second, third = inspect("head", "tail", nil, 42)
t.equal(count, 3)
t.equal(second, nil)
t.equal(third, 42)
t.pack_equal(table.pack(select(-2, "a", "b", "c")), {n = 2, "b", "c"})
t.raises(function() return select(0, "a") end)

-- Lua 5.5 命名 vararg 把结果暴露为带 n 的只读 table 变量。
local invalid, message = load([[
    local function change(... args)
        args = {}
    end
]], "named-vararg-read-only", "t")
t.equal(invalid, nil)
t.equal(type(message), "string")

t.done()
