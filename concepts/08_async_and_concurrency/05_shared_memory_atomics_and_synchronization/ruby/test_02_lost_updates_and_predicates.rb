# 共同问题：如何可执行地展示 lost update，并用状态 predicate 而非 sleep 等待。
# 输入：同步 read/write 阶段、ConditionVariable、Mutex 和 ready flag；观察：确定性覆盖及 while predicate。
# polyglot-family: async_and_concurrency
# polyglot-concept: shared_memory_atomics_and_synchronization
# polyglot-related: languages/ruby/standard_library/11_concurrency_models/
# polyglot-related+: test_082_mutex_condition_variable_and_predicate.rb

require "assertions"

A = PolyglotAssertions

counter = 0
reads_complete = Queue.new
writes_allowed = Queue.new
workers = 2.times.map do
  Thread.new do
    observed = counter
    reads_complete << true
    writes_allowed.pop
    counter = observed + 1
  end
end
2.times { reads_complete.pop }
2.times { writes_allowed << true }
workers.each(&:join)
A.equal(1, counter)

mutex = Mutex.new
condition = ConditionVariable.new
ready = false
producer = Thread.new do
  mutex.synchronize do
    ready = true
    condition.signal
  end
end
mutex.synchronize { condition.wait(mutex) until ready }
producer.join
A.truth(ready)

A.done
