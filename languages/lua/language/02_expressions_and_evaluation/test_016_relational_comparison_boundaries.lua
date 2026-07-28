-- polyglot-covers: lua.expressions.relational_comparison_boundaries

local t = require("support.assertions")

t.truth(3 == 3.0)
t.truth(3 < 4.0)
t.truth("abc" < "abd")
t.truth("same" <= "same")
t.truth(1 ~= "1")
t.raises(function()
    return 1 < "2"
end, "compare")

local nan = 0 / 0
t.falsey(nan == nan)
t.falsey(nan < nan)
t.falsey(nan <= nan)

t.done()
