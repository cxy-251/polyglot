# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.thread-join-value-and-shared-state

require "assertions"

A = PolyglotAssertions

shared = []
commands = Queue.new
worker = Thread.new do
  value = commands.pop
  shared << value
  value * 2
end
commands << 21
A.equal(42, worker.value)
A.equal([21], shared)
A.falsey(worker.alive?)
A.falsey(worker == Thread.current)

previous_report = Thread.report_on_exception
Thread.report_on_exception = false
begin
  failing = Thread.new { raise ArgumentError, "worker failed" }
  joined_error = A.raises(ArgumentError, "worker failed") { failing.join }
  value_error = A.raises(ArgumentError, "worker failed") { failing.value }
  A.same(joined_error, value_error)
  A.falsey(failing.alive?)
ensure
  Thread.report_on_exception = previous_report
end

cancel_error = Class.new(RuntimeError)
ready = Queue.new
release = Queue.new
cancellation_sent = Queue.new
events = []
cancelled_worker = Thread.new do
  Thread.handle_interrupt(cancel_error => :never) do
    events << :critical
    ready << true
    release.pop
    events << :released
  end
rescue cancel_error
  events << :cancelled
end
ready.pop
canceller = Thread.new do
  cancelled_worker.raise(cancel_error, "cancel")
  cancellation_sent << true
end
cancellation_sent.pop
release << true
canceller.join
cancelled_worker.join
A.equal([:critical, :released, :cancelled], events)

# CRuby 以 native threads 运行，但 Ruby 代码受 GVL 约束；共享对象仍需要显式同步。
A.done
