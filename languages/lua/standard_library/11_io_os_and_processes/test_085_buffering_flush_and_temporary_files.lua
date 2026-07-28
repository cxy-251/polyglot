-- polyglot-covers: lua.io.buffering_and_temporary_files

local t = require("support.assertions")
local file = assert(io.tmpfile())

t.truth(file:setvbuf("full", 64))
t.same(file:write("buffered"), file)
t.truth(file:flush())
t.equal(file:seek("set", 0), 0)
t.equal(file:read("a"), "buffered")

t.truth(file:setvbuf("no"))
t.equal(file:seek("end"), 8)
t.same(file:write("!"), file)
t.equal(file:seek("set", 0), 0)
t.equal(file:read("a"), "buffered!")
t.truth(file:close())

t.done()
