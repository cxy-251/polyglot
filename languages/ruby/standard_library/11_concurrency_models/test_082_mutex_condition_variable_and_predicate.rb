# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.mutex-condition-variable-and-predicate

require "assertions"

A = PolyglotAssertions

mutex = Mutex.new
condition = ConditionVariable.new
ready = false
worker = Thread.new do
  mutex.synchronize do
    condition.wait(mutex) until ready
    :observed
  end
end

mutex.synchronize do
  ready = true
  condition.signal
end

A.equal(:observed, worker.value)
A.falsey(worker.alive?)
A.falsey(mutex.locked?)

counter = 0
2.times.map do
  Thread.new { 100.times { mutex.synchronize { counter += 1 } } }
end.each(&:join)
A.equal(200, counter)

A.done
