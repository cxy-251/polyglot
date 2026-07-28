-- polyglot-covers: lua.scope.chunks_and_blocks

local t = require("support.assertions")

local chunk = assert(load([[
    local outside = 10
    do
        local inside = 32
        outside = outside + inside
    end
    return outside
]], "block-example", "t"))

t.equal(chunk(), 42)
t.equal(inside, nil)

local statement_chunk = assert(load("return 6 * 7", "expression", "t"))
t.equal(type(statement_chunk), "function")
t.equal(statement_chunk(), 42)

t.done()
