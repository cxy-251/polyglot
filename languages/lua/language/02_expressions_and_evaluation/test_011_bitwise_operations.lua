-- polyglot-covers: lua.expressions.bitwise_operations

local t = require("support.assertions")

t.equal(0x0f & 0x33, 0x03)
t.equal(0x0f | 0x30, 0x3f)
t.equal(0x0f ~ 0x33, 0x3c)
t.equal(1 << 4, 16)
t.equal(16 >> 3, 2)
t.equal(1 << -1, 0)
t.equal(8 >> -1, 16)
t.equal(~0, -1)
t.equal(1 << (string.packsize("j") * 8), 0)
t.equal(1 >> (string.packsize("j") * 8), 0)
t.raises(function()
    return 1.25 & 1
end)

t.done()
