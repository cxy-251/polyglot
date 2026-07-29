-- Common question: how are calendar fields, UTC, local time, and round trips represented?
-- Inputs: a local calendar table, os.time, local/UTC os.date tables, and normalized fields.
-- Observations: 1-based month fields, local round trips, UTC conversion, and host-zone dependency.
-- polyglot-family: time_locale_and_runtime
-- polyglot-concept: calendar_time_zones_and_arithmetic
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/
-- polyglot-related+: test_086_calendar_conversion_and_platform_boundaries.lua

local t = require("support.assertions")
local timestamp = assert(os.time({
    year = 2026,
    month = 1,
    day = 15,
    hour = 12,
    min = 30,
    sec = 0,
}))
local local_parts = os.date("*t", timestamp)
t.equal(local_parts.year, 2026)
t.equal(local_parts.month, 1)
t.equal(local_parts.day, 15)
t.equal(local_parts.hour, 12)
t.equal(local_parts.min, 30)
t.equal(os.time(local_parts), timestamp)

local utc_parts = os.date("!*t", timestamp)
t.equal(type(utc_parts.year), "number")
t.equal(type(os.date("!%Y-%m-%dT%H:%M:%SZ", timestamp)), "string")

-- Lua 不携带 IANA time-zone database；UTC marker 只转换显示，local zone 由 C runtime/OS 决定。
t.done()
