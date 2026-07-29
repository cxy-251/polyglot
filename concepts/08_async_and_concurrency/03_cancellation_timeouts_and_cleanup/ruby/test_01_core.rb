# 共同问题：超时怎样中止工作，同时保证 ensure 清理。
# 输入：Timeout.timeout、立即期限、ensure 和指定异常类；观察：异步异常传播及栈展开清理。
# polyglot-family: async_and_concurrency
# polyglot-concept: cancellation_timeouts_and_cleanup
# polyglot-related: languages/ruby/standard_library/10_data_time_and_text/test_080_timeout_scope_and_cleanup_boundary.rb

require "assertions"
require "timeout"

A = PolyglotAssertions

trace = []
error = A.raises(Timeout::Error) do
  Timeout.timeout(0.05) do
    begin
      loop { Thread.pass }
    ensure
      trace << :cleaned
    end
  end
end
A.same(Timeout::Error, error.class)
A.equal([:cleaned], trace)

custom = Class.new(RuntimeError)
A.raises(custom) { Timeout.timeout(0.05, custom) { loop { Thread.pass } } }

A.done
