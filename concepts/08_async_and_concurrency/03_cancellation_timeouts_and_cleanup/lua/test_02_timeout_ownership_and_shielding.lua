-- Common question: who owns timeout policy, and can a critical cleanup be shielded?
-- Inputs: an explicit step budget, cooperative yields, a cancellation flag, and coroutine.close.
-- Observations: no built-in timeout, host-driven checkpoints, non-preemption, and guaranteed close cleanup.
-- polyglot-family: async_and_concurrency
-- polyglot-concept: cancellation_timeouts_and_cleanup
-- polyglot-related: languages/lua/language/08_coroutines_and_gc/test_061_coroutine_close_unwinds_resources.lua

local t = require("support.assertions")
local closed = false
local resource = setmetatable({}, {__close = function() closed = true end})
local worker = coroutine.create(function()
    local handle <close> = resource
    for step = 1, 10 do
        coroutine.yield(step)
    end
end)

local budget = 3
for expected = 1, budget do
    local ok, step = coroutine.resume(worker)
    t.truth(ok)
    t.equal(step, expected)
end
t.equal(coroutine.status(worker), "suspended")
t.truth(coroutine.close(worker))
t.truth(closed)

t.equal(rawget(coroutine, "timeout"), nil)
t.equal(rawget(coroutine, "shield"), nil)

t.done()
