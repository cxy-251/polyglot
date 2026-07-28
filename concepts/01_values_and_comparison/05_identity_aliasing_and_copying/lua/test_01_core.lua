-- Common question: when do assignments alias, and what constitutes a copy?
-- Inputs: tables, nested tables, strings, shallow copies, and scalar values.
-- Observations: rawequal, mutation visibility, shallow-copy boundaries, and value types.
-- polyglot-family: values_and_comparison
-- polyglot-concept: identity_aliasing_and_copying
-- polyglot-related: languages/lua/language/01_values_and_types/test_007_reference_identity.lua

local t = require("support.assertions")
local original = {nested = {value = 1}}
local alias = original
local copy = {}
for key, value in pairs(original) do
    copy[key] = value
end

alias.extra = 42
t.equal(original.extra, 42)
t.same(alias, original)
t.falsey(rawequal(copy, original))
t.same(copy.nested, original.nested)

copy.nested.value = 2
t.equal(original.nested.value, 2)
t.truth(rawequal("lua", "lu" .. "a"))

t.done()
