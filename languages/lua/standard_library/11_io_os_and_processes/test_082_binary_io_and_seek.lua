-- polyglot-covers: lua.io.binary_seek

local t = require("support.assertions")
local path = t.temp_path("binary.dat")
local file = assert(io.open(path, "w+b"))
local payload = string.char(0, 1, 127, 128, 255)

t.same(file:write(payload), file)
t.equal(file:seek(), #payload)
t.equal(file:seek("set", 2), 2)
t.equal(file:read(2), string.char(127, 128))
t.equal(file:seek("end", -1), 4)
t.equal(file:read(1), string.char(255))
t.equal(file:read(1), nil)
t.truth(file:close())
t.truth(os.remove(path))

t.done()
