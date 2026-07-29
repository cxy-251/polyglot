-- polyglot-covers: lua.scope.chunks_blocks_and_shadowing

local t = require("support.assertions")

local value = "outer"
local observations = {}
do
    -- 新 local 在初始化表达式求值后才进入作用域，因此右侧读取外层 value。
    local value = value .. "-inner"
    observations[#observations + 1] = value
    do
        local value = "nested"
        observations[#observations + 1] = value
    end
    observations[#observations + 1] = value
end
t.equal(table.concat(observations, ","), "outer-inner,nested,outer-inner")
t.equal(value, "outer")

local environment = {}
local chunk = assert(load([[
    local outside = 10
    do
        local inside = 32
        outside = outside + inside
    end
    leaked = outside
    return outside
]], "block-example", "t", environment))
t.equal(chunk(), 42)
t.equal(environment.leaked, 42)
t.equal(environment.inside, nil)

t.done()
