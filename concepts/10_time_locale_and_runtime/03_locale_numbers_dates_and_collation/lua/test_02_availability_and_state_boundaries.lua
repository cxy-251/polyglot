-- Common question: how is locale availability detected and process-global state restored?
-- Inputs: current locale, guaranteed C locale, an unavailable name, category changes, and restoration.
-- Observations: nil capability result, category scope, process-global mutation, and explicit restore.
-- polyglot-family: time_locale_and_runtime
-- polyglot-concept: locale_numbers_dates_and_collation
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/test_086_time_date_and_differences.lua

local t = require("support.assertions")
local original = assert(os.setlocale(nil, "all"))
local numeric_original = assert(os.setlocale(nil, "numeric"))

t.truth(os.setlocale("C", "numeric"))
t.matches(os.setlocale(nil, "numeric"), "^C")
t.equal(os.setlocale("polyglot_LOCALE_that_does_not_exist", "numeric"), nil)
t.truth(os.setlocale(numeric_original, "numeric"))
t.equal(os.setlocale(nil, "numeric"), numeric_original)
t.equal(os.setlocale(nil, "all"), original)

-- Locale 名称与可用集合由 OS 决定；runner 还用独立进程阻断跨测试泄漏。
t.done()
