-- Common question: how do locale settings affect numbers, dates, and collation?
-- Inputs: current locale, guaranteed C locale, unavailable names, formatting, and string order.
-- Observations: process-global categories, capability failure, explicit restoration, and byte ordering.
-- polyglot-family: time_locale_and_runtime
-- polyglot-concept: locale_numbers_dates_and_collation
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/
-- polyglot-related+: test_086_calendar_conversion_and_platform_boundaries.lua

local t = require("support.assertions")
local original_numeric = assert(os.setlocale(nil, "numeric"))
local original_time = assert(os.setlocale(nil, "time"))

t.with_cleanup(function()
    t.truth(os.setlocale("C", "numeric"))
    t.truth(os.setlocale("C", "time"))
    t.matches(os.setlocale(nil, "numeric"), "^C")
    t.equal(tonumber("1.5"), 1.5)
    t.equal(string.format("%.1f", 1.5), "1.5")

    local january = assert(os.time({year = 2026, month = 1, day = 15, hour = 12}))
    t.equal(os.date("%b", january), "Jan")
    t.equal(os.setlocale("polyglot_LOCALE_that_does_not_exist", "numeric"), nil)
    t.truth("Z" < "a")
end, function()
    os.setlocale(original_numeric, "numeric")
    os.setlocale(original_time, "time")
end)

t.equal(os.setlocale(nil, "numeric"), original_numeric)
t.equal(os.setlocale(nil, "time"), original_time)

-- Locale 集合来自 OS；Lua 字符串 < 始终按字节比较，不调用 locale collation。
t.done()
