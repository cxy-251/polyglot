# 共同问题：部分取得资源后失败怎样回滚，return 是否绕过清理。
# 输入：两次取得、第二次失败、正常 return 和嵌套 ensure；观察：只释放已取得资源及逆序释放。
# polyglot-family: errors_and_resources
# polyglot-concept: resource_cleanup
# polyglot-related: languages/ruby/language/08_exceptions_resources_and_loading/
# polyglot-related+: test_061_block_resources_and_nested_ensure.rb

require "assertions"

A = PolyglotAssertions

def acquire_resources(fail_second:)
  trace = []
  begin
    trace << :first
    begin
      raise "second failed" if fail_second

      trace << :second
      return [:done, trace]
    ensure
      trace << :release_second unless fail_second
    end
  ensure
    trace << :release_first
    $polyglot_cleanup_trace = trace
  end
end

result, = acquire_resources(fail_second: false)
A.equal(:done, result)
A.equal([:first, :second, :release_second, :release_first], $polyglot_cleanup_trace)
A.raises(RuntimeError, "second failed") { acquire_resources(fail_second: true) }
A.equal([:first, :release_first], $polyglot_cleanup_trace)
$polyglot_cleanup_trace = nil

A.done
