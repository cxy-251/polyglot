-- Common question: how are canonically equivalent and malformed Unicode inputs handled?
-- Inputs: composed/decomposed accents, invalid UTF-8 bytes, and code-point iteration.
-- Observations: byte equality, absent normalization, utf8.len failure position, and iterator rejection.
-- polyglot-family: text_binary_and_serialization
-- polyglot-concept: unicode_strings_and_code_units
-- polyglot-related: languages/lua/standard_library/09_strings_patterns_utf8/
-- polyglot-related+: test_072_utf8_codepoints_and_byte_indices.lua

local t = require("support.assertions")
local composed = "\u{00e9}"
local decomposed = "e\u{0301}"

t.falsey(composed == decomposed)
t.equal(utf8.len(composed), 1)
t.equal(utf8.len(decomposed), 2)

local invalid = "A\255B"
local length, invalid_position = utf8.len(invalid)
t.equal(length, nil)
t.equal(invalid_position, 2)
t.raises(function()
    for _ in utf8.codes(invalid) do end
end, "invalid UTF-8 code")

-- 标准 utf8 库不做 Unicode normalization 或 grapheme segmentation。
t.done()
