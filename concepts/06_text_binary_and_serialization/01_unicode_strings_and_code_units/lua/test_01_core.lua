-- Common question: are string indices bytes, code units, code points, or graphemes?
-- Inputs: ASCII, a three-byte code point, an emoji, embedded NUL, and byte offsets.
-- Observations: byte length, utf8.len, utf8.codes positions, and binary safety.
-- polyglot-family: text_binary_and_serialization
-- polyglot-concept: unicode_strings_and_code_units
-- polyglot-related: languages/lua/standard_library/09_strings_patterns_utf8/
-- polyglot-related+: test_072_utf8_codepoints_and_byte_indices.lua

local t = require("support.assertions")
local text = "A中🙂"

t.equal(#text, 8)
t.equal(utf8.len(text), 3)
t.equal(string.byte(text, 2), 0xe4)
t.equal(utf8.offset(text, 2), 2)
t.equal(utf8.offset(text, 3), 5)

local positions = {}
for position, codepoint in utf8.codes(text) do
    positions[#positions + 1] = {position, codepoint}
end
t.equal(positions[2][1], 2)
t.equal(positions[2][2], 0x4e2d)
t.equal(#("A\0B"), 3)

t.done()
