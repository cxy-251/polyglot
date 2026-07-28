-- Common question: how do calendar arithmetic and zone transitions handle invalid/local times?
-- Inputs: normalized out-of-range fields, leap day, elapsed-second addition, and absent zone APIs.
-- Observations: os.time normalization, leap-year behavior, instant arithmetic, and transition-data absence.
-- polyglot-family: time_locale_and_runtime
-- polyglot-concept: calendar_time_zones_and_arithmetic
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/test_086_time_date_and_differences.lua

local t = require("support.assertions")

local normalized = {year = 2026, month = 1, day = 32, hour = 0}
local timestamp = os.time(normalized)
t.equal(os.date("!%Y-%m-%d", timestamp), "2026-02-01")

local leap = os.time({year = 2024, month = 2, day = 29, hour = 0})
t.equal(os.date("!%Y-%m-%d", leap), "2024-02-29")
t.equal(os.date("!%Y-%m-%d", leap + 86400), "2024-03-01")

t.equal(rawget(os, "timezone"), nil)
t.equal(rawget(os, "zoneinfo"), nil)

-- 日历字段归一化不等于具备 DST gap/fold 规则；标准库没有 named-zone arithmetic。
t.done()
