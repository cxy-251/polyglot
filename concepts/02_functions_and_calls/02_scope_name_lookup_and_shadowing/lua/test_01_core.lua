-- Common question: how are local, global, shadowed, and environment names resolved?
-- Inputs: nested locals, _ENV replacement, _G, and an undeclared global.
-- Observations: lexical lookup, right-hand-side timing, environment fields, and 5.5 declarations.
-- polyglot-family: functions_and_calls
-- polyglot-concept: scope_name_lookup_and_shadowing
-- polyglot-related: languages/lua/language/03_scope_and_variables/test_023_global_declarations.lua

local t = require("support.assertions")
local value = 40
do
    local value = value + 2
    t.equal(value, 42)
end
t.equal(value, 40)

local environment = {base = 40}
local chunk = assert(load(
    "global answer, base; answer = base + 2; return answer",
    "scope",
    "t",
    environment
))
t.equal(chunk(), 42)
t.equal(environment.answer, 42)
t.equal(rawget(_G, "answer"), nil)

local invalid, message = load("global allowed; return missing", "undeclared", "t", {})
t.equal(invalid, nil)
t.matches(message, "missing")

t.done()
