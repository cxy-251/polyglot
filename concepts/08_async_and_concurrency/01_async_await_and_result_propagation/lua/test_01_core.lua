-- Common question: how does deferred work suspend and propagate results or failures?
-- Inputs: coroutine.create/resume/yield, multiple results, and a raised table error.
-- Observations: cooperative suspension, explicit result tuples, boolean status, and arbitrary errors.
-- polyglot-family: async_and_concurrency
-- polyglot-concept: async_await_and_result_propagation
-- polyglot-related: languages/lua/language/08_coroutines_and_gc/
-- polyglot-related+: test_057_coroutine_resume_status_and_value_exchange.lua

local t = require("support.assertions")
local worker = coroutine.create(function(input)
    local resumed = coroutine.yield("ready", input)
    return resumed * 2, "done"
end)

local ok, marker, input = coroutine.resume(worker, 21)
t.truth(ok)
t.equal(marker, "ready")
t.equal(input, 21)

local result, state
ok, result, state = coroutine.resume(worker, 21)
t.truth(ok)
t.equal(result, 42)
t.equal(state, "done")

local failing = coroutine.create(function() error({kind = "failed"}) end)
local failure_ok, failure = coroutine.resume(failing)
t.falsey(failure_ok)
t.equal(failure.kind, "failed")

-- Coroutine 不是 async/await runtime；调用方必须显式 resume 并收集结果。
t.done()
