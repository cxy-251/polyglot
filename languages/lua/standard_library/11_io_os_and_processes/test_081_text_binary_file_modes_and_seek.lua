-- polyglot-covers: lua.io.text_binary_file_modes_and_seek

local t = require("support.assertions")
local text_path = t.temp_path("text.txt")
local writer = assert(io.open(text_path, "w"))
t.same(writer:write("first\n", "second\n"), writer)
t.truth(writer:close())

local reader = assert(io.open(text_path, "r"))
t.equal(reader:read("l"), "first")
t.equal(reader:read("L"), "second\n")
t.equal(reader:read("l"), nil)
t.truth(reader:close())
t.truth(os.remove(text_path))

local binary_path = t.temp_path("binary.dat")
local file = assert(io.open(binary_path, "w+b"))
local payload = string.char(0, 1, 127, 128, 255)
t.same(file:write(payload), file)
t.equal(file:seek(), #payload)
t.equal(file:seek("set", 2), 2)
t.equal(file:read(2), string.char(127, 128))
t.equal(file:seek("end", -1), 4)
t.equal(file:read(1), string.char(255))
t.truth(file:close())
t.truth(os.remove(binary_path))

t.done()
