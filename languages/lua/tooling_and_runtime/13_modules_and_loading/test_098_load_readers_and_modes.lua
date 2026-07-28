-- polyglot-covers: lua.modules.load_readers_and_modes

local t = require("support.assertions")
local parts = {"return ", "40", " + ", "2"}
local index = 0
local reader = function()
    index = index + 1
    return parts[index]
end

local chunk = assert(load(reader, "reader-chunk", "t", {}))
t.equal(chunk(), 42)
t.equal(index, #parts + 1)

local bytecode = string.dump(function()
    return "binary"
end)
t.equal(assert(load(bytecode, "binary", "b"))(), "binary")

local invalid_text, text_error = load(bytecode, "binary-as-text", "t")
t.equal(invalid_text, nil)
t.matches(text_error, "binary")

local invalid_binary, binary_error = load("return 1", "text-as-binary", "b")
t.equal(invalid_binary, nil)
t.matches(binary_error, "text")

t.done()
