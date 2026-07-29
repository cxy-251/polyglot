-- Common question: what shared-memory and atomic guarantees exist between execution units?
-- Inputs: two cooperatively interleaved coroutines and a shared table counter.
-- Observations: deterministic lost update, same-state sharing, absent atomics, and no parallel execution.
-- polyglot-family: async_and_concurrency
-- polyglot-concept: shared_memory_atomics_and_synchronization
-- polyglot-related: languages/lua/language/08_coroutines_and_gc/
-- polyglot-related+: test_057_coroutine_resume_status_and_value_exchange.lua

local t = require("support.assertions")
local shared = {value = 0}
local function increment()
    local observed = shared.value
    coroutine.yield("read")
    shared.value = observed + 1
end
local first = coroutine.create(increment)
local second = coroutine.create(increment)

t.pack_equal(table.pack(coroutine.resume(first)), {n = 2, true, "read"})
t.pack_equal(table.pack(coroutine.resume(second)), {n = 2, true, "read"})
t.truth(coroutine.resume(first))
t.truth(coroutine.resume(second))
t.equal(shared.value, 1)

t.equal(rawget(_G, "Atomics"), nil)
t.equal(rawget(_G, "Mutex"), nil)
t.equal(rawget(_G, "Condition"), nil)

-- 这是显式 cooperative interleaving；Lua 标准语言没有 shared-memory thread 或 atomic API。
t.done()
