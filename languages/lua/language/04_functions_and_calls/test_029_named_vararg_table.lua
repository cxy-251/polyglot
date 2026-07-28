-- polyglot-covers: lua.functions.named_vararg_table

local t = require("support.assertions")

local function inspect(first, ... rest)
    t.equal(first, "head")
    t.equal(rest.n, 3)
    t.equal(rest[1], "tail")
    t.equal(rest[2], nil)
    t.equal(rest[3], 42)
    rest[1] = "changed"
    return table.unpack(rest, 1, rest.n)
end

t.pack_equal(
    table.pack(inspect("head", "tail", nil, 42)),
    {n = 3, "changed", nil, 42}
)

local invalid, message = load([[
    local function change(... args)
        args = {}
    end
]], "named-vararg-read-only", "t")
t.equal(invalid, nil)
t.matches(message, "read%-only")

t.done()
