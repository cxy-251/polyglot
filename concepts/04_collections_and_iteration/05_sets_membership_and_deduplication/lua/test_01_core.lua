-- Common question: how are membership and deduplication represented without a built-in set?
-- Inputs: repeated scalars, table identities, false members, nil, and NaN.
-- Observations: key-based membership, identity semantics, false-vs-absence, and forbidden keys.
-- polyglot-family: collections_and_iteration
-- polyglot-concept: sets_membership_and_deduplication
-- polyglot-related: languages/lua/language/05_tables_and_iteration/
-- polyglot-related+: test_033_table_keys_constructors_and_absence.lua

local t = require("support.assertions")
local set = {}
for _, value in ipairs({"a", "b", "a"}) do
    set[value] = true
end
t.truth(set.a)
t.truth(set.b)
t.equal(set.c, nil)

local first = {}
local second = {}
set[first] = true
t.truth(set[first])
t.equal(set[second], nil)

set.false_member = false
t.truth(rawget(set, "false_member") ~= nil)
t.raises(function() set[nil] = true end)
t.raises(function() set[0 / 0] = true end)

t.done()
