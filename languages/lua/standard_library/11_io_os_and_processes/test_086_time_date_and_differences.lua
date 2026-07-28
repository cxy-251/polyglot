-- polyglot-covers: lua.os.time_date_and_differences

local t = require("support.assertions")

local epoch = 0
t.equal(os.date("!%Y-%m-%d %H:%M:%S", epoch), "1970-01-01 00:00:00")

local parts = os.date("!*t", epoch)
t.equal(parts.year, 1970)
t.equal(parts.month, 1)
t.equal(parts.day, 1)
t.equal(parts.hour, 0)
t.equal(parts.min, 0)
t.equal(parts.sec, 0)

local first = os.time({year = 2026, month = 1, day = 1, hour = 0})
local second = os.time({year = 2026, month = 1, day = 2, hour = 0})
t.equal(os.difftime(second, first), 86400.0)
t.equal(type(os.clock()), "number")

t.done()
