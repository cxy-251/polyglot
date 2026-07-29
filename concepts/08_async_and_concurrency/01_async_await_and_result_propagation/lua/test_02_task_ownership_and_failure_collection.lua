-- Common question: who owns a spawned unit and observes its failure and cleanup?
-- Inputs: a suspended coroutine, an unobserved error, coroutine.close, and coroutine.wrap.
-- Observations: caller-owned resume, explicit failure collection, deterministic close, and wrap propagation.
-- polyglot-family: async_and_concurrency
-- polyglot-concept: async_await_and_result_propagation
-- polyglot-related: languages/lua/language/08_coroutines_and_gc/
-- polyglot-related+: test_060_coroutine_errors_wrap_and_explicit_close.lua

local t = require("support.assertions")
local closed = 0
local resource = setmetatable({}, {__close = function() closed = closed + 1 end})
local worker = coroutine.create(function()
    local handle <close> = resource
    t.same(handle, resource)
    coroutine.yield("owned")
    error("worker failed")
end)

t.pack_equal(table.pack(coroutine.resume(worker)), {n = 2, true, "owned"})
local ok, error_value = coroutine.resume(worker)
t.falsey(ok)
t.matches(error_value, "worker failed")
t.equal(closed, 0)
local close_ok, close_error = coroutine.close(worker)
t.falsey(close_ok)
t.matches(close_error, "worker failed")
t.equal(closed, 1)

local wrapped = coroutine.wrap(function() error("wrapped failure") end)
t.raises(wrapped, "wrapped failure")

t.done()
