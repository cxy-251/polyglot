# frozen_string_literal: true
# polyglot-covers: ruby.errors.exception-cause-and-backtrace

require "assertions"

A = PolyglotAssertions

class WrappedCourseError < StandardError
end

def raise_wrapped_error
  raise ArgumentError, "inner"
rescue ArgumentError
  raise WrappedCourseError, "outer"
end

error = A.raises(WrappedCourseError, "outer") { raise_wrapped_error }
A.same(ArgumentError, error.cause.class)
A.equal("inner", error.cause.message)
A.truth(error.backtrace_locations.any?)
A.equal(File.expand_path(__FILE__), error.backtrace_locations.first.absolute_path)

explicit = WrappedCourseError.new("explicit")
explicit.set_backtrace(["course.rb:1"])
A.equal(["course.rb:1"], explicit.backtrace)

A.done
