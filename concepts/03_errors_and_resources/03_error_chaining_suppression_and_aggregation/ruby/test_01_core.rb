# 共同问题：高层异常怎样保留低层 cause，何时显式抑制因果链。
# 输入：rescue 中包装、显式 cause:nil 和 backtrace；观察：自动链接、抑制及类型信息。
# polyglot-family: errors_and_resources
# polyglot-concept: error_chaining_suppression_and_aggregation
# polyglot-related: languages/ruby/language/08_exceptions_resources_and_loading/
# polyglot-related+: test_058_exception_cause_and_backtrace.rb

require "assertions"

A = PolyglotAssertions

wrapped = begin
  begin
    raise IOError, "disk"
  rescue IOError
    raise RuntimeError, "load failed"
  end
rescue => error
  error
end
A.same(RuntimeError, wrapped.class)
A.same(IOError, wrapped.cause.class)
A.equal("disk", wrapped.cause.message)

suppressed = begin
  raise ArgumentError, "public", cause: nil
rescue => error
  error
end
A.nil_value(suppressed.cause)

A.done
