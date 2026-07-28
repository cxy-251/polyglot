-- polyglot-covers: lua.scope.local_shadowing

local t = require("support.assertions")

local value = "outer"
local observations = {}

do
    local value = value .. "-inner"
    observations[#observations + 1] = value
    do
        local value = "nested"
        observations[#observations + 1] = value
    end
    observations[#observations + 1] = value
end

t.equal(observations[1], "outer-inner")
t.equal(observations[2], "nested")
t.equal(observations[3], "outer-inner")
t.equal(value, "outer")

t.done()
