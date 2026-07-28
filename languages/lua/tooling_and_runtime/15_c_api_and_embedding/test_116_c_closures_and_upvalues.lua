-- polyglot-covers: lua.c_api.c_closures_and_upvalues

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("closures"), "C API case passed: closures")

local native = require("polyglot_native")
local counter = native.counter(40)
t.equal(counter(), 41)
t.equal(counter(), 42)
t.equal(counter(8), 50)

t.done()
