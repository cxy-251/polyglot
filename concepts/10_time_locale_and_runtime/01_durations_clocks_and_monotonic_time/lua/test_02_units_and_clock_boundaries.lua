-- Common question: what units, precision, and arithmetic boundaries do clocks expose?
-- Inputs: epoch seconds, difftime, os.clock fractions, negative durations, and date formatting.
-- Observations: seconds as numbers, signed differences, explicit calendar conversion, and no duration type.
-- polyglot-family: time_locale_and_runtime
-- polyglot-concept: durations_clocks_and_monotonic_time
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/test_086_time_date_and_differences.lua

local t = require("support.assertions")

t.equal(os.date("!%Y-%m-%d", 0), "1970-01-01")
t.equal(os.difftime(10, 3), 7.0)
t.equal(os.difftime(3, 10), -7.0)
t.equal(type(os.clock()), "number")
t.equal(type(os.time()), "number")

local duration = os.difftime(3, 1)
t.equal(type(duration), "number")
t.equal(duration * 1000, 2000.0)
t.equal(rawget(os, "Duration"), nil)

-- Lua 没有 duration/instant 类型；调用方必须标明数字单位和时钟来源。
t.done()
