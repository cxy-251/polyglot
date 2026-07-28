-- polyglot-covers: lua.values.reference_identity

local t = require("support.assertions")

local first = {}
local alias = first
local distinct = {}

t.same(alias, first)
t.falsey(rawequal(first, distinct))
t.falsey(first == distinct)

local function callable()
    return 42
end

t.same(callable, callable)
t.falsey(rawequal(callable, function() return 42 end))

local coroutine_value = coroutine.create(function() end)
t.same(coroutine_value, coroutine_value)

t.done()
