-- Common question: how are absence, missing keys, and present false values represented?
-- Inputs: nil, false, an absent table key, and a deleted key.
-- Observations: type, rawget, membership encoding, and nil assignment.
-- polyglot-family: values_and_comparison
-- polyglot-concept: null_missing_and_optional_values
-- polyglot-related: languages/lua/language/01_values_and_types/
-- polyglot-related+: test_002_values_truthiness_and_absence.lua

local t = require("support.assertions")
local values = {present_false = false, present_value = 42}

t.equal(type(nil), "nil")
t.equal(values.missing, nil)
t.equal(rawget(values, "missing"), nil)
t.equal(values.present_false, false)
t.truth(values.present_false ~= nil)

values.present_value = nil
t.equal(values.present_value, nil)
t.equal(next(values), "present_false")

-- Lua 没有独立的 null/optional 值；table 中写入 nil 同时表示删除键。
t.done()
