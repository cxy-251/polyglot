-- polyglot-covers: lua.debug.upvalue_identity_join_and_loaded_environments

local t = require("support.assertions")
local function make(value)
    return function() return value end
end

local first = make("first")
local second = make("second")
t.falsey(debug.upvalueid(first, 1) == debug.upvalueid(second, 1))
debug.upvaluejoin(second, 1, first, 1)
t.truth(debug.upvalueid(first, 1) == debug.upvalueid(second, 1))
t.equal(debug.setupvalue(first, 1, "joined"), "value")
t.equal(first(), "joined")
t.equal(second(), "joined")

local chunk = assert(load("return answer", "environment-upvalue", "t"))
local name, original_environment = debug.getupvalue(chunk, 1)
t.equal(name, "_ENV")
t.same(original_environment, _G)
local environment = {answer = 42}
t.equal(debug.setupvalue(chunk, 1, environment), "_ENV")
t.equal(chunk(), 42)
t.equal(rawget(_G, "answer"), nil)

-- upvaluejoin 改写闭包共享关系；它不是普通 lexical scope 的替代方案。
t.done()
