-- polyglot-covers: lua.io.text_file_roundtrip

local t = require("support.assertions")
local path = t.temp_path("text.txt")
local writer = assert(io.open(path, "w"))

t.same(writer:write("first\n", "second\n"), writer)
t.truth(writer:close())
t.equal(io.type(writer), "closed file")

local reader = assert(io.open(path, "r"))
t.equal(reader:read("l"), "first")
t.equal(reader:read("L"), "second\n")
t.equal(reader:read("l"), nil)
t.truth(reader:close())
t.truth(os.remove(path))

t.done()
