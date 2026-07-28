-- Common question: how are binary values encoded, sliced, and interpreted by endianness?
-- Inputs: unsigned/signed integers, floats, embedded zeros, and substrings.
-- Observations: immutable string buffers, explicit pack formats, byte slicing, and next offset.
-- polyglot-family: text_binary_and_serialization
-- polyglot-concept: binary_buffers_views_and_endianness
-- polyglot-related: languages/lua/standard_library/09_strings_patterns_utf8/test_070_binary_pack_and_unpack.lua

local t = require("support.assertions")

local little = string.pack("<I2i4", 0x1234, -42)
local big = string.pack(">I2i4", 0x1234, -42)
t.equal(string.byte(little, 1), 0x34)
t.equal(string.byte(big, 1), 0x12)

local unsigned, signed, next_position = string.unpack("<I2i4", little)
t.equal(unsigned, 0x1234)
t.equal(signed, -42)
t.equal(next_position, #little + 1)

local prefix = string.sub(little, 1, 2)
t.equal(#prefix, 2)
t.equal(little, string.pack("<I2i4", 0x1234, -42))

-- Lua strings are immutable byte buffers; substring produces a value, not a mutable view.
t.done()
