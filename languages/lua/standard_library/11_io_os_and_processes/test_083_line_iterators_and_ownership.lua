-- polyglot-covers: lua.io.line_iterators_and_ownership

local t = require("support.assertions")
local path = t.temp_path("lines.txt")
local writer = assert(io.open(path, "w"))
assert(writer:write("alpha\nbeta\ngamma\n"))
assert(writer:close())

local lines = {}
for line in io.lines(path) do
    lines[#lines + 1] = line
end
t.equal(table.concat(lines, ","), "alpha,beta,gamma")

local reader = assert(io.open(path, "r"))
local iterator = reader:lines()
t.equal(iterator(), "alpha")
t.equal(io.type(reader), "file")
t.truth(reader:close())
t.raises(iterator, "already closed")

t.truth(os.remove(path))
t.done()
