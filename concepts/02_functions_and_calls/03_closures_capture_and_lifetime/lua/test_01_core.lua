-- Common question: what does a closure capture, and how long does captured state live?
-- Inputs: a mutable local, sibling closures, independent factories, and collection.
-- Observations: shared upvalue identity, mutation visibility, lifetime, and factory isolation.
-- polyglot-family: functions_and_calls
-- polyglot-concept: closures_capture_and_lifetime
-- polyglot-related: languages/lua/language/03_scope_and_variables/
-- polyglot-related+: test_019_closure_upvalue_lifetime_and_sharing.lua

local t = require("support.assertions")

local function cell(initial)
    local value = initial
    return function() return value end, function(next_value) value = next_value end
end

local get, set = cell(40)
t.equal(get(), 40)
set(42)
t.equal(get(), 42)
t.truth(debug.upvalueid(get, 1) == debug.upvalueid(set, 1))

collectgarbage("collect")
t.equal(get(), 42)
local other_get = cell(40)
t.equal(other_get(), 40)
t.falsey(debug.upvalueid(get, 1) == debug.upvalueid(other_get, 1))

t.done()
