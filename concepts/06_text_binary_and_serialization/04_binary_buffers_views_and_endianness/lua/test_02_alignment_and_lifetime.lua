-- Common question: how do alignment and owner lifetime constrain binary access?
-- Inputs: native/aligned formats, packed formats, immutable strings, and C userdata.
-- Observations: explicit packsize, padding, retained string ownership, and checked userdata closure.
-- polyglot-family: text_binary_and_serialization
-- polyglot-concept: binary_buffers_views_and_endianness
-- polyglot-related: languages/lua/tooling_and_runtime/15_c_api_and_embedding/test_119_userdata_user_values_and_gc.lua

local t = require("support.assertions")

local packed_size = string.packsize("=I1I4")
local aligned_size = string.packsize("!4=I1I4")
t.truth(aligned_size >= packed_size)

local encoded = string.pack("!4=I1I4", 1, 42)
local first, second = string.unpack("!4=I1I4", encoded)
t.equal(first, 1)
t.equal(second, 42)

local native = require("polyglot_native")
local box = native.new_box(42, encoded)
t.equal(box:get(), 42)
t.equal(box:label(), encoded)
box:close()
t.raises(function() box:get() end, "box is closed")

t.done()
