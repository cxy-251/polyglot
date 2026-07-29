# 共同问题：clock 单位、精度和 calendar conversion 边界是什么。
# 输入：float seconds、integer nanoseconds、clock_getres 和 Time.at；观察：显式单位、分辨率及 epoch 转换。
# polyglot-family: time_locale_and_runtime
# polyglot-concept: durations_clocks_and_monotonic_time
# polyglot-related: languages/ruby/standard_library/10_data_time_and_text/test_075_date_time_and_calendar_arithmetic.rb

require "assertions"

A = PolyglotAssertions

seconds = Process.clock_gettime(Process::CLOCK_MONOTONIC, :float_second)
nanoseconds = Process.clock_gettime(Process::CLOCK_MONOTONIC, :nanosecond)
A.truth(seconds.is_a?(Float))
A.truth(nanoseconds.is_a?(Integer))
A.truth(nanoseconds.positive?)

resolution = Process.clock_getres(Process::CLOCK_MONOTONIC, :nanosecond)
A.truth(resolution.is_a?(Integer))
A.truth(resolution.positive?)

epoch = Time.at(0).utc
A.equal(0, epoch.to_i)
A.equal("1970-01-01 00:00:00 UTC", epoch.to_s)

A.done
