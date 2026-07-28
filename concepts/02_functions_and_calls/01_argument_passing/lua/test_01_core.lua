-- Common question: how are missing, extra, named, and multi-result arguments bound?
-- Inputs: too few/many arguments, varargs containing nil, and a multi-result call.
-- Observations: nil fill, truncation, named vararg table, and last-position adjustment.
-- polyglot-family: functions_and_calls
-- polyglot-concept: argument_passing
-- polyglot-related: languages/lua/language/04_functions_and_calls/test_029_named_vararg_table.lua

local t = require("support.assertions")

local function fixed(first, second)
    return first, second
end
t.pack_equal(table.pack(fixed("only")), {n = 2, "only", nil})
t.pack_equal(table.pack(fixed(1, 2, 3)), {n = 2, 1, 2})

local function variadic(first, ... rest)
    return first, rest.n, rest[1], rest[2]
end
t.pack_equal(
    table.pack(variadic("head", "tail", nil)),
    {n = 4, "head", 2, "tail", nil}
)

local function pair() return 10, 20 end
t.pack_equal(table.pack(fixed(pair())), {n = 2, 10, 20})

t.done()
