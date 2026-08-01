# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.thread-local-and-fiber-local-state

require "assertions"

A = PolyglotAssertions

A.case("Thread#[] is fiber-local while thread_variable_set spans fibers in one thread") do
  fiber_key = :polyglot_fiber_local
  thread_key = :polyglot_thread_local
  original_fiber_value = Thread.current[fiber_key]
  original_thread_value = Thread.current.thread_variable_get(thread_key)

  begin
    Thread.current[fiber_key] = :main_fiber
    Thread.current.thread_variable_set(thread_key, :main_thread)

    fiber = Fiber.new do
      before = Thread.current[fiber_key]
      thread_value = Thread.current.thread_variable_get(thread_key)
      Thread.current[fiber_key] = :child_fiber
      [before, thread_value, Thread.current[fiber_key]]
    end

    A.equal([nil, :main_thread, :child_fiber], fiber.resume)
    A.equal(:main_fiber, Thread.current[fiber_key])
    A.equal(:main_thread, Thread.current.thread_variable_get(thread_key))

    worker = Thread.new do
      [Thread.current[fiber_key], Thread.current.thread_variable_get(thread_key)]
    end
    A.equal([nil, nil], worker.value)
  ensure
    Thread.current[fiber_key] = original_fiber_value
    Thread.current.thread_variable_set(thread_key, original_thread_value)
  end
end

A.done
