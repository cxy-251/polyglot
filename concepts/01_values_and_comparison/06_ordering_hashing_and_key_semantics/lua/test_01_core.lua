-- Common question: which values are orderable, and how are mapping keys normalized?
-- Inputs: numbers, strings, tables, integer-valued floats, nil, and NaN.
-- Observations: relational errors, __lt, identity keys, and forbidden keys.
-- polyglot-family: values_and_comparison
-- polyglot-concept: ordering_hashing_and_key_semantics
-- polyglot-related: languages/lua/language/05_tables_and_iteration/
-- polyglot-related+: test_033_table_keys_constructors_and_absence.lua

local t = require("support.assertions")

t.truth(1 < 2.0)
t.truth("a" < "b")
t.raises(function() return 1 < "2" end)

local ordered = {__lt = function(left, right) return left.rank < right.rank end}
t.truth(setmetatable({rank = 1}, ordered) < setmetatable({rank = 2}, ordered))

local keys = {}
keys[1.0] = "normalized"
t.equal(keys[1], "normalized")
local object = {}
keys[object] = "identity"
t.equal(keys[{}], nil)
t.raises(function() keys[nil] = true end)
t.raises(function() keys[0 / 0] = true end)

t.done()
