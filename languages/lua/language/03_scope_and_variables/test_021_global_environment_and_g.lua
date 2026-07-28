-- polyglot-covers: lua.scope.global_environment_and_g

local t = require("support.assertions")

t.same(_G, _ENV)
local original_g = _G

local environment = {answer = 42}
setmetatable(environment, {__index = original_g})

local chunk = assert(load(
    "return answer, type(print), _G == _ENV",
    "custom-environment",
    "t",
    environment
))
local answer, print_type, g_is_environment = chunk()
t.equal(answer, 42)
t.equal(print_type, "function")
t.falsey(g_is_environment)
t.same(environment._G, original_g)

t.done()
