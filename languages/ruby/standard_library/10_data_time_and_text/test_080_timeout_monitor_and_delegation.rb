# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.timeout-monitor-and-delegation

require "assertions"
require "delegate"
require "forwardable"
require "monitor"
require "timeout"

A = PolyglotAssertions

A.equal(:done, Timeout.timeout(1) { :done })
A.raises(Timeout::Error) { Timeout.timeout(0.02) { Queue.new.pop } }

monitor = Monitor.new
value = monitor.synchronize { 42 }
A.equal(42, value)

forwarder_class = Class.new do
  extend Forwardable
  def_delegator :@target, :upcase, :upper

  def initialize(target)
    @target = target
  end
end
A.equal("RUBY", forwarder_class.new("ruby").upper)

delegator = SimpleDelegator.new([1, 2])
A.equal(2, delegator.length)
delegator.__setobj__([1, 2, 3])
A.equal(3, delegator.length)

A.done
