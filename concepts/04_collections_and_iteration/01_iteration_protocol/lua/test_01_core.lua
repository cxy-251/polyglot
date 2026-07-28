-- Common question: what protocol drives ordinary collection iteration?
-- Inputs: array-like and mapping-like tables, pairs, ipairs, and next.
-- Observations: yielded key/value pairs, hole termination, and unspecified mapping order.
-- polyglot-family: collections_and_iteration
-- polyglot-concept: iteration_protocol
-- polyglot-related: languages/lua/language/05_tables_and_iteration/test_037_next_pairs_and_unspecified_order.lua

local t = require("support.assertions")

local sequence = {"a", "b", nil, "d"}
local visited = {}
for index, value in ipairs(sequence) do
    visited[#visited + 1] = {index, value}
end
t.equal(#visited, 2)
t.equal(visited[2][2], "b")

local mapping = {alpha = 1, beta = 2}
local copied = {}
for key, value in pairs(mapping) do
    copied[key] = value
end
t.equal(copied.alpha, 1)
t.equal(copied.beta, 2)

local key, value = next({answer = 42})
t.equal(key, "answer")
t.equal(value, 42)

t.done()
