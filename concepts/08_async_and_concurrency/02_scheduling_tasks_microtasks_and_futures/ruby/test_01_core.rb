# 共同问题：谁调度 ready work，执行到哪个边界才交回控制。
# 输入：两个 Fiber、resume、yield 和事件日志；观察：caller 控制调度、run-to-yield 及无 microtask 队列。
# polyglot-family: async_and_concurrency
# polyglot-concept: scheduling_tasks_microtasks_and_futures
# polyglot-related: languages/ruby/standard_library/11_concurrency_models/test_085_fiber_resume_yield_and_transfer.rb

require "assertions"

A = PolyglotAssertions

events = []
first = Fiber.new do
  events << :first_start
  Fiber.yield(:first_pause)
  events << :first_end
  :first_result
end
second = Fiber.new do
  events << :second
  :second_result
end

A.equal(:first_pause, first.resume)
A.equal([:first_start], events)
A.equal(:second_result, second.resume)
A.equal([:first_start, :second], events)
A.equal(:first_result, first.resume)
A.equal([:first_start, :second, :first_end], events)

A.done
