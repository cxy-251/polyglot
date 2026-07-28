-- polyglot-covers: lua.utf8.codepoints_and_byte_indices

local t = require("support.assertions")
local text = "A中🙂"

t.equal(#text, 8)
t.equal(utf8.len(text), 3)
t.equal(utf8.codepoint(text, 1), 65)
t.equal(utf8.char(0x41, 0x4e2d, 0x1f642), text)

local positions = {}
for position, codepoint in utf8.codes(text) do
    positions[#positions + 1] = {position, codepoint}
end
t.equal(positions[1][1], 1)
t.equal(positions[2][1], 2)
t.equal(positions[3][1], 5)
t.equal(utf8.offset(text, 3), 5)

local position, final_position = utf8.offset(text, 2)
t.equal(position, 2)
t.equal(final_position, 4)

-- utf8 库使用 code point 和字节索引，不提供 grapheme cluster 或 normalization。
t.done()
