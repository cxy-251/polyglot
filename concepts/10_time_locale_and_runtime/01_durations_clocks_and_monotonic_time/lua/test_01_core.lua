-- Common question: which clocks measure wall time, elapsed duration, or process CPU?
-- Inputs: os.time, os.difftime, os.clock, signed differences, and unit conversion.
-- Observations: numeric seconds, CPU-time capability, explicit units, and absent monotonic clock.
-- polyglot-family: time_locale_and_runtime
-- polyglot-concept: durations_clocks_and_monotonic_time
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/
-- polyglot-related+: test_086_calendar_conversion_and_platform_boundaries.lua

local t = require("support.assertions")

t.equal(os.difftime(10, 3), 7.0)
t.equal(os.difftime(3, 10), -7.0)
t.equal(type(os.time()), "number")
local cpu_before = os.clock()
local total = 0
for index = 1, 10000 do total = total + index end
local cpu_after = os.clock()
t.equal(total, 50005000)
t.truth(cpu_after >= cpu_before)

local duration_seconds = os.difftime(3, 1)
t.equal(type(duration_seconds), "number")
t.equal(duration_seconds * 1000, 2000.0)
t.equal(rawget(os, "Duration"), nil)
t.equal(rawget(os, "monotonic"), nil)

-- Lua 没有 duration/instant 类型或通用 monotonic wall clock；
-- 数字必须携带应用约定的单位和来源。
t.done()
