-- Common question: what are indexing origins, slice rules, and out-of-range results?
-- Inputs: sequence tables, strings, positive/negative string bounds, and missing indices.
-- Observations: 1-based table access, nil misses, byte slicing, and absent native table slices.
-- polyglot-family: collections_and_iteration
-- polyglot-concept: indexing_slicing_and_bounds
-- polyglot-related: languages/lua/language/05_tables_and_iteration/
-- polyglot-related+: test_035_sequences_borders_holes_and_length.lua

local t = require("support.assertions")
local values = {"zero?", "one", "two"}

t.equal(values[1], "zero?")
t.equal(values[0], nil)
t.equal(values[4], nil)
t.equal(string.sub("abcdef", 2, 4), "bcd")
t.equal(string.sub("abcdef", -3, -1), "def")
t.equal(string.byte("A中", 2), 0xe4)

local slice = {}
table.move(values, 2, 3, 1, slice)
t.equal(table.concat(slice, ","), "one,two")

-- Table 没有内建 slice/view；范围复制需要显式循环或 table.move。
t.done()
