# 共同问题：body 与多个 cleanup 同时失败时怎样保留信息。
# 输入：body 失败和两层 ensure 失败；观察：外层失败占优，较早失败沿 cause 链保留。
# polyglot-family: errors_and_resources
# polyglot-concept: error_chaining_suppression_and_aggregation
# polyglot-related: languages/ruby/language/08_exceptions_resources_and_loading/
# polyglot-related+: test_058_exception_cause_and_backtrace.rb

require "assertions"

A = PolyglotAssertions

final = begin
  begin
    begin
      raise RuntimeError, "body"
    ensure
      raise ArgumentError, "inner cleanup"
    end
  ensure
    raise IOError, "outer cleanup"
  end
rescue => error
  error
end

A.same(IOError, final.class)
A.equal("outer cleanup", final.message)
A.same(ArgumentError, final.cause.class)
A.equal("inner cleanup", final.cause.message)
A.same(RuntimeError, final.cause.cause.class)
A.equal("body", final.cause.cause.message)

A.done
