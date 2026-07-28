-- Common question: how do locale settings affect numbers, dates, and collation?
-- Inputs: isolated C locale, tonumber, string.format, os.date, and bytewise string order.
-- Observations: numeric conversion, formatted decimal, locale date text, and lexical byte ordering.
-- polyglot-family: time_locale_and_runtime
-- polyglot-concept: locale_numbers_dates_and_collation
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/test_086_time_date_and_differences.lua

local t = require("support.assertions")

t.matches(os.setlocale(nil, "numeric"), "^C")
t.matches(os.setlocale(nil, "time"), "^C")
t.equal(tonumber("1.5"), 1.5)
t.equal(string.format("%.1f", 1.5), "1.5")
t.equal(os.date("!%a", 0), "Thu")
t.truth("Z" < "a")

-- Lua 的 < 对字符串比较字节序，不调用 locale collation；标准库也没有 locale-aware formatter。
t.done()
