-- Common question: which clocks measure wall time, elapsed duration, or process CPU?
-- Inputs: os.time, os.difftime, os.clock, and two fixed UTC instants.
-- Observations: second-based calendar time, numeric durations, CPU-time capability, and monotonic gap.
-- polyglot-family: time_locale_and_runtime
-- polyglot-concept: durations_clocks_and_monotonic_time
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/test_086_time_date_and_differences.lua

local t = require("support.assertions")
local first = os.time({year = 2026, month = 1, day = 1, hour = 0})
local second = os.time({year = 2026, month = 1, day = 2, hour = 0})

t.equal(os.difftime(second, first), 86400.0)
t.equal(type(os.time()), "number")
local cpu_before = os.clock()
local total = 0
for index = 1, 10000 do total = total + index end
local cpu_after = os.clock()
t.equal(total, 50005000)
t.truth(cpu_after >= cpu_before)

t.equal(rawget(os, "monotonic"), nil)

-- os.clock 是实现定义的程序 CPU 时间入口，不替代通用 monotonic wall clock。
t.done()
