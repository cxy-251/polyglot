-- Common question: when does newly ready work run relative to current work?
-- Inputs: an explicit FIFO queue, tasks that enqueue tasks, and coroutine resumptions.
-- Observations: queue policy belongs to the host, current callback completion, and explicit ready boundaries.
-- polyglot-family: async_and_concurrency
-- polyglot-concept: scheduling_tasks_microtasks_and_futures
-- polyglot-related: languages/lua/language/08_coroutines_and_gc/test_057_coroutine_resume_and_results.lua

local t = require("support.assertions")
local queue = {}
local events = {}
local function schedule(callback)
    queue[#queue + 1] = callback
end

schedule(function()
    events[#events + 1] = "outer:start"
    schedule(function() events[#events + 1] = "inner" end)
    events[#events + 1] = "outer:end"
end)
schedule(function() events[#events + 1] = "peer" end)

while #queue > 0 do
    local callback = table.remove(queue, 1)
    callback()
end
t.equal(table.concat(events, ","), "outer:start,outer:end,peer,inner")

-- 该队列是宿主策略示例，不是 Lua 标准 event loop、future 或 microtask API。
t.done()
