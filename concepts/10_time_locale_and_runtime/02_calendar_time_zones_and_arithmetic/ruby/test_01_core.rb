# 共同问题：calendar fields、UTC、local time 和 roundtrip 怎样表示。
# 输入：Date、Time.utc、fixed-offset Time、ISO 8601 和 epoch；观察：1-based 月份、UTC offset 及 roundtrip。
# polyglot-family: time_locale_and_runtime
# polyglot-concept: calendar_time_zones_and_arithmetic
# polyglot-related: languages/ruby/standard_library/10_data_time_and_text/
# polyglot-related+: test_075_calendar_time_zones_and_monotonic_clocks.rb

require "assertions"
require "date"
require "time"

A = PolyglotAssertions

date = Date.new(2026, 7, 29)
A.equal([2026, 7, 29], [date.year, date.month, date.day])

utc = Time.utc(2026, 7, 29, 12, 34, 56)
A.truth(utc.utc?)
A.equal(0, utc.utc_offset)
A.equal(utc, Time.iso8601(utc.iso8601))
A.equal(utc.to_i, Time.at(utc.to_i).utc.to_i)

offset = Time.new(2026, 7, 29, 12, 34, 56, "+05:30")
A.equal(19_800, offset.utc_offset)
A.equal(Time.utc(2026, 7, 29, 7, 4, 56), offset.utc)

A.done
