-- polyglot-covers: lua.io.iterators_default_streams_and_ownership

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
t.raises(iterator)
t.truth(os.remove(path))

local original_output = io.output()
local temporary = assert(io.tmpfile())
t.with_cleanup(function()
    io.output(temporary)
    t.truth(temporary:setvbuf("full", 64))
    io.write("buffered")
    t.truth(temporary:flush())
    t.equal(temporary:seek("set", 0), 0)
    t.equal(temporary:read("a"), "buffered")
end, function()
    io.output(original_output)
    temporary:close()
end)
t.same(io.output(), original_output)
t.equal(io.type(temporary), "closed file")

-- io.lines(filename) 拥有并在结束时关闭文件；file:lines() 的 handle 仍由调用者拥有。
t.done()
