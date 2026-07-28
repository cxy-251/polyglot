-- Common question: how is an invocation receiver or context bound?
-- Inputs: dot calls, colon calls, detached methods, and callable tables.
-- Observations: explicit self insertion, detached-call requirements, and __call.
-- polyglot-family: functions_and_calls
-- polyglot-concept: callable_binding_and_invocation_context
-- polyglot-related: languages/lua/language/04_functions_and_calls/test_030_method_calls_and_callable_tables.lua

local t = require("support.assertions")
local object = {value = 40}
function object:add(amount)
    return self.value + amount
end

t.equal(object:add(2), 42)
t.equal(object.add(object, 2), 42)

local detached = object.add
t.equal(detached(object, 2), 42)
t.raises(function() return detached(2) end, "index")

local callable = setmetatable({value = 40}, {
    __call = function(self, amount) return self.value + amount end,
})
t.equal(callable(2), 42)

t.done()
