-- Common question: which values are accepted as conditions, and which are false?
-- Inputs: nil, false, numeric zero, empty string, and empty table.
-- Observations: branch selection, operand-returning and/or, and non-overridable truth.
-- polyglot-family: values_and_comparison
-- polyglot-concept: truthiness
-- polyglot-related: languages/lua/language/01_values_and_types/test_002_nil_boolean_and_truth.lua

local t = require("support.assertions")

t.falsey(nil)
t.falsey(false)
t.truth(0)
t.truth("")
t.truth({})
t.equal(0 and "taken", "taken")
t.equal(false or "fallback", "fallback")

local value = setmetatable({}, {__len = function() return 0 end})
t.truth(value)

t.done()
