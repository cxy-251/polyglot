-- polyglot-covers: lua.values.nil_boolean_and_truth

local t = require("support.assertions")

t.falsey(false)
t.falsey(nil)
t.truth(0)
t.truth(0.0)
t.truth("")
t.truth({})

local chosen = 0 and "zero remains truthy"
t.equal(chosen, "zero remains truthy")
t.equal((nil or "fallback"), "fallback")

t.done()
