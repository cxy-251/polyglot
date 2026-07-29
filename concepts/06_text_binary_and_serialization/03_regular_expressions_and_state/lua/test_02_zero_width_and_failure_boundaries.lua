-- Common question: how do zero-width matches and invalid patterns terminate?
-- Inputs: frontier patterns, empty captures, malformed classes, and gsub callbacks.
-- Observations: boundary positions, finite advancement, syntax errors, and callback failure propagation.
-- polyglot-family: text_binary_and_serialization
-- polyglot-concept: regular_expressions_and_state
-- polyglot-related: languages/lua/standard_library/09_strings_patterns_utf8/
-- polyglot-related+: test_067_pattern_language_iteration_and_substitution.lua

local t = require("support.assertions")

local start_position, end_position = string.find(" a", "%f[%a]")
t.equal(start_position, 2)
t.equal(end_position, 1)

local positions = {}
for position in string.gmatch("ab", "()") do
    positions[#positions + 1] = position
end
t.equal(table.concat(positions, ","), "1,2,3")

t.raises(function() string.match("abc", "[") end)
t.raises(function()
    string.gsub("a", ".", function() error("replacement failed") end)
end, "replacement failed")

t.done()
