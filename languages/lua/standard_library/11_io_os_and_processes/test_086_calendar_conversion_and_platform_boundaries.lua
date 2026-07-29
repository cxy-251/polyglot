-- polyglot-covers: lua.os.calendar_conversion_and_platform_boundaries

local t = require("support.assertions")

local timestamp = assert(os.time({
    year = 2026,
    month = 1,
    day = 15,
    hour = 12,
    min = 30,
    sec = 0,
}))
local parts = os.date("*t", timestamp)
t.equal(parts.year, 2026)
t.equal(parts.month, 1)
t.equal(parts.day, 15)
t.equal(parts.hour, 12)
t.equal(parts.min, 30)
t.equal(os.difftime(timestamp, timestamp), 0.0)
t.equal(type(os.date("!%Y-%m-%d", timestamp)), "string")
t.equal(type(os.clock()), "number")

-- time_t 范围、时区数据库、DST 与本地日历跳变来自 C runtime/OS；
-- 因此不把 epoch 格式、一天固定 86400 秒或可用时区写成 Lua 保证。
t.done()
