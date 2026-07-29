# 共同问题：并发工作怎样返回结果和失败，等待是否自动取得结果。
# 输入：成功 Thread、失败 Thread、join 和 value；观察：join/value 都传播失败，value 取得成功结果。
# polyglot-family: async_and_concurrency
# polyglot-concept: async_await_and_result_propagation
# polyglot-related: languages/ruby/standard_library/11_concurrency_models/test_081_thread_join_value_and_shared_state.rb

require "assertions"

A = PolyglotAssertions

success = Thread.new { 21 * 2 }
A.same(success, success.join)
A.equal(42, success.value)

failure = Thread.new { raise ArgumentError, "worker failed" }
failure.report_on_exception = false
A.raises(ArgumentError, "worker failed") { failure.join }
error = A.raises(ArgumentError, "worker failed") { failure.value }
A.equal("worker failed", error.message)

# Ruby 没有 async/await 关键字；Thread#value 是本对照中的结果收集入口。
A.falsey(Kernel.respond_to?(:await))

A.done
