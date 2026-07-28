-- Common question: how should waiting use state predicates rather than timing guesses?
-- Inputs: an explicit readiness predicate, a producer coroutine, a consumer loop, and finite resumes.
-- Observations: predicate recheck, value publication, no sleep, and absent mutex/condition primitives.
-- polyglot-family: async_and_concurrency
-- polyglot-concept: shared_memory_atomics_and_synchronization
-- polyglot-related: languages/lua/language/08_coroutines_and_gc/test_059_yield_value_exchange.lua

local t = require("support.assertions")
local state = {ready = false}
local producer = coroutine.create(function()
    coroutine.yield("working")
    state.value = 42
    state.ready = true
end)

local resumes = 0
while not state.ready do
    local ok = coroutine.resume(producer)
    t.truth(ok)
    resumes = resumes + 1
    t.truth(resumes <= 2)
end
t.equal(resumes, 2)
t.equal(state.value, 42)
t.equal(rawget(_G, "Mutex"), nil)
t.equal(rawget(_G, "Condition"), nil)

-- Predicate loop 是当前宿主的 cooperative 协议，不伪装成线程 condition variable。
t.done()
