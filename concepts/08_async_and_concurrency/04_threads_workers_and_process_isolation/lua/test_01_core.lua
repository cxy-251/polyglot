-- Common question: are execution units shared-memory threads, workers, or isolated runtimes?
-- Inputs: Lua coroutines, the C host's two states, globals, and registries.
-- Observations: cooperative same-state coroutines, independent C states, and absent standard worker API.
-- polyglot-family: async_and_concurrency
-- polyglot-concept: threads_workers_and_process_isolation
-- polyglot-related: languages/lua/tooling_and_runtime/16_advanced_c_api_and_compatibility/
-- polyglot-related+: test_123_multiple_state_isolation.lua

local t = require("support.assertions")
local c_api = require("support.c_api")
local shared = {value = 40}
local worker = coroutine.create(function()
    shared.value = shared.value + 2
end)
t.truth(coroutine.resume(worker))
t.equal(shared.value, 42)

t.matches(
    c_api.run("state-isolation"),
    "C API case passed: state%-isolation"
)
t.equal(rawget(_G, "Thread"), nil)
t.equal(rawget(_G, "Worker"), nil)

-- Coroutine 共享同一 state 且不并行；多个 state 由宿主创建并隔离，不是标准 worker runtime。
t.done()
