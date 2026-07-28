-- polyglot-covers: lua.table_library.sequence_mutation

local t = require("support.assertions")
local values = {"a", "c"}

table.insert(values, 2, "b")
t.equal(table.concat(values, ","), "a,b,c")
t.equal(table.remove(values, 2), "b")
t.equal(table.concat(values, ","), "a,c")

table.insert(values, "d")
t.equal(values[3], "d")
t.equal(table.remove(values), "d")

local destination = {}
t.same(table.move(values, 1, 2, 1, destination), destination)
t.equal(destination[1], "a")
t.equal(destination[2], "c")

t.done()
