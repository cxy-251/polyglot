# frozen_string_literal: true
# polyglot-covers: ruby.errors.thread-exception-propagation

require "assertions"

A = PolyglotAssertions

previous_report = Thread.report_on_exception
Thread.report_on_exception = false

begin
  worker = Thread.new { raise ArgumentError, "worker failed" }
  joined_error = A.raises(ArgumentError, "worker failed") { worker.join }
  A.falsey(worker.alive?)
  error = A.raises(ArgumentError, "worker failed") { worker.value }
  A.same(joined_error, error)
  A.truth(error.backtrace_locations.any?)
ensure
  Thread.report_on_exception = previous_report
end

successful = Thread.new { 6 * 7 }
A.equal(42, successful.value)
A.falsey(successful.alive?)

A.done
