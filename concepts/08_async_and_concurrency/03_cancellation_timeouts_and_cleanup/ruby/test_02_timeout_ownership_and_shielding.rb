# 共同问题：谁拥有取消策略，关键清理区能否延迟异步异常。
# 输入：Thread#raise、handle_interrupt、Queue 同步和 ensure；观察：显式 owner、masked 区域完成及随后交付。
# polyglot-family: async_and_concurrency
# polyglot-concept: cancellation_timeouts_and_cleanup
# polyglot-related: languages/ruby/standard_library/11_concurrency_models/
# polyglot-related+: test_081_thread_results_shared_state_and_failures.rb

require "assertions"

A = PolyglotAssertions

cancel_error = Class.new(RuntimeError)
ready = Queue.new
release = Queue.new
raise_started = Queue.new
events = []

worker = Thread.new do
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
  raise_started << true
  worker.raise(cancel_error, "cancel")
end
raise_started.pop
release << true
canceller.join
worker.join
A.equal([:critical, :released, :cancelled], events)

A.done
