-- Common question: what schedules ready work and determines execution order?
-- Inputs: two coroutines, explicit resume calls, yields, and an event log.
-- Observations: caller-controlled scheduling, run-until-yield behavior, FIFO only when implemented, and no microtasks.
-- polyglot-family: async_and_concurrency
-- polyglot-concept: scheduling_tasks_microtasks_and_futures
-- polyglot-related: languages/lua/language/08_coroutines_and_gc/
-- polyglot-related+: test_057_coroutine_resume_status_and_value_exchange.lua

local t = require("support.assertions")
local events = {}
local function worker(name)
    return coroutine.create(function()
        events[#events + 1] = name .. ":start"
        coroutine.yield()
        events[#events + 1] = name .. ":end"
    end)
end

local first = worker("first")
local second = worker("second")
t.truth(coroutine.resume(first))
t.truth(coroutine.resume(second))
t.truth(coroutine.resume(second))
t.truth(coroutine.resume(first))
t.equal(table.concat(events, ","), "first:start,second:start,second:end,first:end")

t.equal(rawget(_G, "queueMicrotask"), nil)
t.equal(rawget(_G, "Promise"), nil)

-- Lua 没有标准 ready queue；执行顺序就是宿主调用 resume 的顺序，
-- FIFO、优先级和新任务何时运行都必须由宿主 runtime 另行定义。
t.done()
