# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.thread-local-and-fiber-local-state

require "assertions"

A = PolyglotAssertions

Thread.current[:fiber_local] = :main_fiber
Thread.current.thread_variable_set(:thread_local, :main_thread)

fiber = Fiber.new do
  before = Thread.current[:fiber_local]
  thread_value = Thread.current.thread_variable_get(:thread_local)
  Thread.current[:fiber_local] = :child_fiber
  [before, thread_value, Thread.current[:fiber_local]]
end

A.equal([nil, :main_thread, :child_fiber], fiber.resume)
A.equal(:main_fiber, Thread.current[:fiber_local])
A.equal(:main_thread, Thread.current.thread_variable_get(:thread_local))

worker = Thread.new do
  [
    Thread.current[:fiber_local],
    Thread.current.thread_variable_get(:thread_local)
  ]
end
A.equal([nil, nil], worker.value)

A.done
