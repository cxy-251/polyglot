-- Common question: how can suspended work be cancelled while preserving cleanup?
-- Inputs: a coroutine with a to-be-closed resource, a yield point, and coroutine.close.
-- Observations: explicit cancellation ownership, pending resource lifetime, reverse unwind, and dead state.
-- polyglot-family: async_and_concurrency
-- polyglot-concept: cancellation_timeouts_and_cleanup
-- polyglot-related: languages/lua/language/08_coroutines_and_gc/test_061_coroutine_close_unwinds_resources.lua

local t = require("support.assertions")
local events = {}
local resource = setmetatable({}, {
    __close = function(_, error_value)
        events[#events + 1] = {kind = "closed", error = error_value}
    end,
})
local worker = coroutine.create(function()
    local handle <close> = resource
    t.same(handle, resource)
    coroutine.yield("waiting")
end)

local ok, marker = coroutine.resume(worker)
t.truth(ok)
t.equal(marker, "waiting")
t.equal(#events, 0)
t.truth(coroutine.close(worker))
t.equal(#events, 1)
t.equal(events[1].error, nil)
t.equal(coroutine.status(worker), "dead")

t.done()
