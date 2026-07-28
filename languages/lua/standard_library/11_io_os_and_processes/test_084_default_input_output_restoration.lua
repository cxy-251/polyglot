-- polyglot-covers: lua.io.default_stream_restoration

local t = require("support.assertions")
local output_path = t.temp_path("default-output.txt")
local input_path = t.temp_path("default-input.txt")
local original_output = io.output()
local original_input = io.input()

local output = assert(io.open(output_path, "w"))
io.output(output)
io.write("captured")
io.output(original_output)
t.truth(output:close())

local input_writer = assert(io.open(input_path, "w"))
assert(input_writer:write("42\n"))
assert(input_writer:close())
local input = assert(io.open(input_path, "r"))
io.input(input)
t.equal(io.read("n"), 42)
io.input(original_input)
t.truth(input:close())

local reader = assert(io.open(output_path, "r"))
t.equal(reader:read("a"), "captured")
t.truth(reader:close())
t.truth(os.remove(output_path))
t.truth(os.remove(input_path))

t.done()
