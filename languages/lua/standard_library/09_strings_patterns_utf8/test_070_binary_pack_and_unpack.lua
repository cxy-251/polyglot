-- polyglot-covers: lua.strings.binary_pack_and_unpack

local t = require("support.assertions")

local encoded = string.pack("<I2i4fd", 0x1234, -42, 1.5, 2.25)
t.equal(#encoded, string.packsize("<I2i4fd"))

local unsigned, signed, float_value, double_value, next_position =
    string.unpack("<I2i4fd", encoded)
t.equal(unsigned, 0x1234)
t.equal(signed, -42)
t.near(float_value, 1.5, 1e-6)
t.near(double_value, 2.25, 1e-12)
t.equal(next_position, #encoded + 1)

local padded = string.pack("c4", "xy")
t.equal(padded, "xy\0\0")

t.done()
