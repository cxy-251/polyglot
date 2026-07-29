# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.fiber-scheduler-interface

require "assertions"

A = PolyglotAssertions

scheduler_class = Class.new do
  attr_reader :closed

  def block(_blocker, _timeout = nil)
    false
  end

  def unblock(_blocker, _fiber)
    nil
  end

  def kernel_sleep(_duration = nil)
    0
  end

  def io_wait(_io, _events, _timeout = nil)
    0
  end

  def fiber_interrupt(_fiber, _exception)
    nil
  end

  def close
    @closed = true
  end
end

A.nil_value(Fiber.scheduler)
scheduler = scheduler_class.new
Fiber.set_scheduler(scheduler)
A.same(scheduler, Fiber.scheduler)
Fiber.set_scheduler(nil)
A.nil_value(Fiber.scheduler)
A.truth(scheduler.closed)

A.done
