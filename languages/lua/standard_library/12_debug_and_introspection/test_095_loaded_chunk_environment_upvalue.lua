-- polyglot-covers: lua.debug.loaded_chunk_environment

local t = require("support.assertions")
local chunk = assert(load("return answer", "environment-upvalue", "t"))
local name, original_environment = debug.getupvalue(chunk, 1)
t.equal(name, "_ENV")
t.same(original_environment, _G)

local environment = {answer = 42}
t.equal(debug.setupvalue(chunk, 1, environment), "_ENV")
t.equal(chunk(), 42)

local _, observed_environment = debug.getupvalue(chunk, 1)
t.same(observed_environment, environment)
t.equal(rawget(_G, "answer"), nil)

t.done()
