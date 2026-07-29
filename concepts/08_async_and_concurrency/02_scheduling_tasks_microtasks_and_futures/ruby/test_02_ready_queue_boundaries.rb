# 共同问题：当前 callback 新增的 ready work 相对当前工作何时执行。
# 输入：显式 FIFO Queue、会继续 enqueue 的任务和循环；观察：当前 callback 完成后才取下一个任务。
# polyglot-family: async_and_concurrency
# polyglot-concept: scheduling_tasks_microtasks_and_futures
# polyglot-related: languages/ruby/standard_library/11_concurrency_models/test_083_queue_sized_queue_and_close.rb

require "assertions"

A = PolyglotAssertions

ready = Queue.new
events = []
ready << proc do
  events << :first_start
  ready << proc { events << :nested }
  events << :first_end
end
ready << proc { events << :second }

ready.pop.call until ready.empty?
A.equal([:first_start, :first_end, :second, :nested], events)

# 这只是应用定义的 FIFO；Ruby 语言没有 JavaScript 式 microtask queue。
A.falsey(defined?(Microtask))

A.done
