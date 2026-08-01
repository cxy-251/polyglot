# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.mutex-condition-variable-and-predicate

require "assertions"
require "monitor"

A = PolyglotAssertions

A.case("ConditionVariable wait is guarded by a predicate under the same Mutex") do
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
  A.falsey(mutex.locked?)
end

A.case("Mutex serializes a compound read-modify-write update") do
  mutex = Mutex.new
  counter = 0
  2.times.map do
    Thread.new { 100.times { mutex.synchronize { counter += 1 } } }
  end.each(&:join)
  A.equal(200, counter)
end

A.case("Monitor is reentrant while Mutex rejects recursive locking by one thread") do
  monitor = Monitor.new
  mutex = Mutex.new
  A.equal(:nested, monitor.synchronize { monitor.synchronize { :nested } })
  A.raises(ThreadError) { mutex.synchronize { mutex.synchronize {} } }
end

A.done
