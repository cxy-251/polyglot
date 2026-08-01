# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.timeout-monitor-and-delegation

require "assertions"
require "timeout"

A = PolyglotAssertions

A.case("a nil timeout executes the block without installing a deadline") do
  A.equal(:done, Timeout.timeout(nil) { :done })
end

A.case("timeout interruption still runs ensure cleanup inside the block") do
  events = []
  error = A.raises(Timeout::Error) do
    Timeout.timeout(0.02) do
      begin
        events << :entered
        Queue.new.pop
      ensure
        events << :cleanup
      end
    end
  end
  A.equal(%i[entered cleanup], events)
  A.truth(error.is_a?(Timeout::Error))
end

A.case("the caller may choose the exception class used to interrupt the block") do
  custom_timeout = Class.new(StandardError)
  A.raises(custom_timeout) { Timeout.timeout(0.02, custom_timeout) { Queue.new.pop } }
end
A.done
