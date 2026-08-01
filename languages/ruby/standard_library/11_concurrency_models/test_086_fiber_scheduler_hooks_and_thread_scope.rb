# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.fiber-scheduler-interface

require "assertions"

A = PolyglotAssertions

scheduler_class = Class.new do
  attr_reader :events

  def initialize
    @events = []
  end

  def block(_blocker, _timeout = nil)
    false
  end

  def unblock(_blocker, _fiber)
    nil
  end

  def kernel_sleep(duration = nil)
    @events << [:sleep, duration]
    0
  end

  def io_wait(_io, events, _timeout = nil)
    events
  end

  def fiber_interrupt(_fiber, _exception)
    nil
  end

  def fiber(&operation)
    @events << :fiber
    Fiber.new(blocking: false, &operation).tap(&:resume)
  end

  def close
    @events << :close
  end
end

A.case("Fiber.schedule requires a scheduler installed on the current thread") do
  A.nil_value(Fiber.scheduler)
  A.raises(RuntimeError) { Fiber.schedule {} }
end

A.case("a thread-local scheduler owns scheduled fibers, hooks and close cleanup") do
  scheduler = scheduler_class.new
  begin
    Fiber.set_scheduler(scheduler)
    A.same(scheduler, Fiber.scheduler)
    A.nil_value(Thread.new { Fiber.scheduler }.value)
    scheduled = Fiber.schedule do
      scheduler.events << :before_sleep
      sleep(0)
      scheduler.events << :after_sleep
      :finished
    end
    A.falsey(scheduled.alive?)
    A.includes(scheduler.events, :fiber)
    A.includes(scheduler.events, [:sleep, 0])
    A.includes(scheduler.events, :after_sleep)
  ensure
    Fiber.set_scheduler(nil)
  end
  A.nil_value(Fiber.scheduler)
  A.equal(:close, scheduler.events.last)
end

A.done
