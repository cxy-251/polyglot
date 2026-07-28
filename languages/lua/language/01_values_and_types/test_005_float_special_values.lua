-- polyglot-covers: lua.values.float_special_values

local t = require("support.assertions")

local infinity = math.huge
local nan = 0.0 / 0.0

t.truth(infinity > math.maxinteger)
t.equal(-infinity, -math.huge)
t.falsey(nan == nan)
t.truth(nan ~= nan)
t.equal(1 / infinity, 0.0)
t.equal(math.type(infinity), "float")
t.equal(math.type(nan), "float")

t.done()
