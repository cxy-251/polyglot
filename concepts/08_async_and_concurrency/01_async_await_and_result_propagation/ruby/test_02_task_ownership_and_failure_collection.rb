# 共同问题：谁拥有启动的工作单元，并负责观察失败和清理。
# 输入：Thread、ensure、显式 join/value 和未启用 abort_on_exception；观察：caller 收集结果及 worker 清理。
# polyglot-family: async_and_concurrency
# polyglot-concept: async_await_and_result_propagation
# polyglot-related: languages/ruby/standard_library/11_concurrency_models/
# polyglot-related+: test_081_thread_results_shared_state_and_failures.rb

require "assertions"

A = PolyglotAssertions

trace = Queue.new
worker = Thread.new do
  begin
    trace << :started
    raise "owned failure"
  ensure
    trace << :cleaned
  end
end
worker.report_on_exception = false
A.raises(RuntimeError, "owned failure") { worker.join }
A.equal(:started, trace.pop)
A.equal(:cleaned, trace.pop)
A.falsey(worker.alive?)
A.raises(RuntimeError, "owned failure") { worker.value }
A.falsey(Thread.abort_on_exception)

A.done
