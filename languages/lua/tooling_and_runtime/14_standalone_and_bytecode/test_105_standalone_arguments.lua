-- polyglot-covers: lua.standalone.arguments

local t = require("support.assertions")
local path = t.temp_path("arguments.lua")
local output_path = t.temp_path("arguments.out")
local file = assert(io.open(path, "w"))
assert(file:write([[
print(arg[-1] ~= nil, arg[0]:match("arguments%.lua$") ~= nil, arg[1], arg[2])
]]))
assert(file:close())

local command = string.format("lua -E %q alpha beta > %q", path, output_path)
t.truth(os.execute(command))
local output = assert(io.open(output_path, "r"))
t.equal(output:read("l"), "true\ttrue\talpha\tbeta")
t.truth(output:close())
t.truth(os.remove(path))
t.truth(os.remove(output_path))

t.done()
