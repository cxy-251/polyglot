# 共同问题：calendar arithmetic、无效日期和 zone transition 数据怎样处理。
# 输入：月底、闰日、elapsed seconds、Date invalid value 和固定 offset；观察：月份裁剪、错误与 instant arithmetic。
# polyglot-family: time_locale_and_runtime
# polyglot-concept: calendar_time_zones_and_arithmetic
# polyglot-related: languages/ruby/standard_library/10_data_time_and_text/test_075_date_time_and_calendar_arithmetic.rb

require "assertions"
require "date"

A = PolyglotAssertions

A.equal(Date.new(2026, 2, 28), Date.new(2026, 1, 31) >> 1)
A.equal(Date.new(2024, 2, 29), Date.new(2024, 2, 28) + 1)
A.raises(Date::Error) { Date.new(2026, 2, 30) }

instant = Time.new(2026, 1, 1, 0, 0, 0, "+05:30")
A.equal(19_800, instant.utc_offset)
A.equal(60.0, (instant + 60) - instant)
A.equal("+0530", instant.strftime("%z"))

# Core Time 接受 fixed offset；IANA transition database 不是 Ruby 语言接口。
A.falsey(Time.respond_to?(:zoneinfo))

A.done
