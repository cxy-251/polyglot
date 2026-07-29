# 共同问题：wall clock、monotonic clock 和 duration arithmetic 怎样区分。
# 输入：Time.now、Process::CLOCK_MONOTONIC、固定 instants 和负 duration；观察：时钟用途、数值单位和有符号差。
# polyglot-family: time_locale_and_runtime
# polyglot-concept: durations_clocks_and_monotonic_time
# polyglot-related: languages/ruby/standard_library/10_data_time_and_text/
# polyglot-related+: test_075_calendar_time_zones_and_monotonic_clocks.rb

require "assertions"
require "time"

A = PolyglotAssertions

wall = Time.now
A.truth(wall.is_a?(Time))
before = Process.clock_gettime(Process::CLOCK_MONOTONIC)
100.times { 1 + 1 }
after = Process.clock_gettime(Process::CLOCK_MONOTONIC)
A.truth(after >= before)

start = Time.iso8601("2026-01-01T00:00:00Z")
finish = Time.iso8601("2026-01-01T00:01:30Z")
A.near(90.0, finish - start)
A.near(-90.0, start - finish)
A.equal(finish, start + 90)

A.done
