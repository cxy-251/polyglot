-- Common question: which numeric models exist, and where does conversion occur?
-- Inputs: integers, floats, numeric strings, fractions, overflow, and invalid text.
-- Observations: math.type, mixed arithmetic, tonumber, math.tointeger, and wrapping.
-- polyglot-family: values_and_comparison
-- polyglot-concept: numeric_models_and_conversion
-- polyglot-related: languages/lua/language/01_values_and_types/
-- polyglot-related+: test_003_number_subtypes_range_and_special_values.lua

local t = require("support.assertions")

t.equal(math.type(42), "integer")
t.equal(math.type(42.0), "float")
t.equal(math.type(1 + 0.5), "float")
t.equal(tonumber("2a", 16), 42)
t.equal(math.tointeger(42.0), 42)
t.equal(math.tointeger(42.5), nil)
t.equal("40" + 2, 42)
t.equal(tonumber("forty-two"), nil)
t.equal(math.maxinteger + 1, math.mininteger)

t.done()
