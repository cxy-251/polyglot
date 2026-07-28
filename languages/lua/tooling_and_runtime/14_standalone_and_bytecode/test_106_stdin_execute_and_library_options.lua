-- polyglot-covers: lua.standalone.stdin_execute_and_library_options

local t = require("support.assertions")
local output_path = t.temp_path("standalone.out")

local execute_command = string.format("lua -E -e 'print(6 * 7)' > %q", output_path)
t.truth(os.execute(execute_command))
local output = assert(io.open(output_path, "r"))
t.equal(output:read("l"), "42")
t.truth(output:close())

local stdin_command = string.format("printf 'print(40 + 2)\\n' | lua -E - > %q", output_path)
t.truth(os.execute(stdin_command))
output = assert(io.open(output_path, "r"))
t.equal(output:read("l"), "42")
t.truth(output:close())

t.truth(os.remove(output_path))
t.done()
