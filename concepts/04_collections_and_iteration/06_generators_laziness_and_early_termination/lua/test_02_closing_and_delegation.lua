-- Common question: who owns cleanup when a suspended producer is abandoned?
-- Inputs: a coroutine producer, yielded values, a to-be-closed resource, and explicit close.
-- Observations: suspension retains resources, coroutine.close unwinds, and delegation is explicit.
-- polyglot-family: collections_and_iteration
-- polyglot-concept: generators_laziness_and_early_termination
-- polyglot-related: languages/lua/language/08_coroutines_and_gc/test_061_coroutine_close_unwinds_resources.lua

local t = require("support.assertions")
local closed = false
local resource = setmetatable({}, {__close = function() closed = true end})
local producer = coroutine.create(function()
    local handle <close> = resource
    t.same(handle, resource)
    coroutine.yield(1)
    coroutine.yield(2)
end)

local ok, value = coroutine.resume(producer)
t.truth(ok)
t.equal(value, 1)
t.falsey(closed)
t.truth(coroutine.close(producer))
t.truth(closed)
t.equal(coroutine.status(producer), "dead")

-- Lua 不提供 yield-from 语法；producer delegation 需要显式 resume/yield 循环。
t.done()
