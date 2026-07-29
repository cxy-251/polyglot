-- Common question: how do failures propagate and how can callers classify them?
-- Inputs: string and table error objects, nested calls, pcall, and xpcall.
-- Observations: unchanged error identity, explicit classification, and message transformation.
-- polyglot-family: errors_and_resources
-- polyglot-concept: exception_propagation_and_matching
-- polyglot-related: languages/lua/language/07_errors_and_resources/
-- polyglot-related+: test_049_error_values_protected_calls_and_context.lua

local t = require("support.assertions")
local marker = {kind = "validation", code = 42}
local function inner()
    error(marker)
end
local function outer()
    inner()
end

local ok, error_value = pcall(outer)
t.falsey(ok)
t.same(error_value, marker)
t.equal(error_value.kind, "validation")

local handled, transformed = xpcall(outer, function(value)
    return {kind = "handled", cause = value}
end)
t.falsey(handled)
t.equal(transformed.kind, "handled")
t.same(transformed.cause, marker)

local rethrow_ok, rethrown = pcall(function()
    local inner_ok, inner_error = pcall(inner)
    if not inner_ok then error(inner_error) end
end)
t.falsey(rethrow_ok)
t.same(rethrown, marker)

t.done()
