-- polyglot-covers: lua.functions.argument_adjustment

local t = require("support.assertions")

local function fixed(first, second)
    return first, second
end

local first, second = fixed("only")
t.equal(first, "only")
t.equal(second, nil)

first, second = fixed("one", "two", "ignored")
t.equal(first, "one")
t.equal(second, "two")

local function results()
    return 10, 20, 30
end

first, second = fixed(results())
t.equal(first, 10)
t.equal(second, 20)

t.done()
