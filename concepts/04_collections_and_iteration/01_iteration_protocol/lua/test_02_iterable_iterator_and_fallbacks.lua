-- Common question: how are custom iterables, iterator state, and fallbacks represented?
-- Inputs: a closure iterator, generic-for triple, __pairs, and a plain table.
-- Observations: explicit iterator/state/control values, closure state, and metamethod fallback.
-- polyglot-family: collections_and_iteration
-- polyglot-concept: iteration_protocol
-- polyglot-related: languages/lua/language/06_metatables_and_objects/
-- polyglot-related+: test_044_operator_and_iteration_metamethods.lua

local t = require("support.assertions")

local function iterator(state, control)
    local next_index = control + 1
    local value = state[next_index]
    if value ~= nil then return next_index, value end
end

local collected = {}
for index, value in iterator, {"a", "b"}, 0 do
    collected[index] = value
end
t.equal(table.concat(collected), "ab")

local wrapped = setmetatable({storage = {answer = 42}}, {
    __pairs = function(self) return next, self.storage, nil end,
})
local key, value = next(wrapped.storage)
t.equal(key, "answer")
t.equal(value, 42)
for observed_key, observed_value in pairs(wrapped) do
    t.equal(observed_key, "answer")
    t.equal(observed_value, 42)
end

t.done()
