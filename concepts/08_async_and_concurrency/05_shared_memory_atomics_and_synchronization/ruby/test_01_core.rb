# 共同问题：共享内存读写、原子操作和同步由什么保证。
# 输入：Thread、共享计数器、Mutex 和 Queue；观察：锁保护复合更新，Queue 提供线程安全 handoff。
# polyglot-family: async_and_concurrency
# polyglot-concept: shared_memory_atomics_and_synchronization
# polyglot-related: languages/ruby/standard_library/11_concurrency_models/
# polyglot-related+: test_082_mutex_condition_variable_and_predicate.rb

require "assertions"

A = PolyglotAssertions

counter = 0
lock = Mutex.new
threads = 4.times.map do
  Thread.new do
    100.times { lock.synchronize { counter += 1 } }
  end
end
threads.each(&:join)
A.equal(400, counter)

queue = Queue.new
producer = Thread.new { queue << :ready }
A.equal(:ready, queue.pop)
producer.join
A.truth(queue.empty?)

# CRuby 的 GVL 不是语言级 atomic API；复合状态仍使用 Mutex 或并发容器。
A.falsey(defined?(Atomic))

A.done
