# 共同问题：重新抛出是否保留异常身份，body 与 ensure 都失败时哪个完成占优。
# 输入：bare raise、body 异常和 ensure 异常；观察：身份保留、最终异常及自动 cause。
# polyglot-family: errors_and_resources
# polyglot-concept: exception_propagation_and_matching
# polyglot-related: languages/ruby/language/08_exceptions_resources_and_loading/
# polyglot-related+: test_058_exception_cause_and_backtrace.rb

require "assertions"

A = PolyglotAssertions

original = RuntimeError.new("body")
rethrown = begin
  begin
    raise original
  rescue
    raise
  end
rescue => error
  error
end
A.same(original, rethrown)

replacement = begin
  begin
    raise original
  ensure
    raise ArgumentError, "cleanup"
  end
rescue => error
  error
end
A.same(ArgumentError, replacement.class)
A.equal("cleanup", replacement.message)
A.same(original, replacement.cause)

A.done
