-- Common question: how can a callable be adapted or partially applied?
-- Inputs: a binary function, fixed leading arguments, methods, and callable tables.
-- Observations: closure adapters, preserved multi-results, explicit receivers, and identity.
-- polyglot-family: functions_and_calls
-- polyglot-concept: callable_adaptation_and_partial_application
-- polyglot-related: languages/lua/language/04_functions_and_calls/test_030_method_calls_and_callable_tables.lua

local t = require("support.assertions")

local function bind_first(callable, fixed)
    return function(...)
        return callable(fixed, ...)
    end
end

local function divide(left, right)
    return left // right, left % right
end
local divide_42 = bind_first(divide, 42)
t.pack_equal(table.pack(divide_42(5)), {n = 2, 8, 2})

local object = {base = 40, add = function(self, amount) return self.base + amount end}
local bound_method = bind_first(object.add, object)
t.equal(bound_method(2), 42)
t.falsey(rawequal(bound_method, object.add))

t.done()
