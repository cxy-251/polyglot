-- Common question: how are calendar fields, UTC, local time, and round trips represented?
-- Inputs: Unix epoch, os.date tables, os.time, UTC format markers, and local tables.
-- Observations: 1-based month fields, UTC conversion, local-zone dependency, and table normalization.
-- polyglot-family: time_locale_and_runtime
-- polyglot-concept: calendar_time_zones_and_arithmetic
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/test_086_time_date_and_differences.lua

local t = require("support.assertions")
local utc = os.date("!*t", 0)
t.equal(utc.year, 1970)
t.equal(utc.month, 1)
t.equal(utc.day, 1)
t.equal(utc.hour, 0)
t.equal(os.date("!%Y-%m-%dT%H:%M:%SZ", 0), "1970-01-01T00:00:00Z")

local local_parts = os.date("*t", 0)
t.equal(local_parts.year, 1970)
t.equal(local_parts.month, 1)
t.equal(local_parts.day, 1)
t.equal(os.time(local_parts), 0)

-- TZ=UTC 由隔离 runner 固定；Lua 标准库不携带 IANA time-zone database。
t.done()
