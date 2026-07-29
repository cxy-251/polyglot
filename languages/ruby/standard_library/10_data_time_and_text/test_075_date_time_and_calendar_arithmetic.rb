# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.date-time-and-calendar-arithmetic

require "assertions"
require "date"
require "time"

A = PolyglotAssertions

date = Date.new(2026, 7, 29)
A.equal(Date.new(2026, 7, 30), date + 1)
A.equal(2, (date + 2) - date)
A.truth(Date.leap?(2024))
A.equal(Date.new(2026, 2, 28), Date.new(2026, 1, 31) >> 1)

instant = Time.iso8601("2026-07-29T12:34:56Z")
A.truth(instant.utc?)
A.equal(0, instant.utc_offset)
A.equal("2026-07-29T12:34:56Z", instant.iso8601)
A.equal(60.0, (instant + 60) - instant)

monotonic_before = Process.clock_gettime(Process::CLOCK_MONOTONIC, :nanosecond)
100.times { 1 + 1 }
monotonic_after = Process.clock_gettime(Process::CLOCK_MONOTONIC, :nanosecond)
A.truth(monotonic_after >= monotonic_before)
A.truth(Process.clock_getres(Process::CLOCK_MONOTONIC, :nanosecond).positive?)

A.done
