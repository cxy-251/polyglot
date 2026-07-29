# 共同问题：异常怎样跨调用传播，调用方怎样按层级匹配。
# 输入：ArgumentError、StandardError、未匹配类和 rescue 变量；观察：最近匹配、对象身份与传播。
# polyglot-family: errors_and_resources
# polyglot-concept: exception_propagation_and_matching
# polyglot-related: languages/ruby/language/08_exceptions_resources_and_loading/test_057_rescue_else_ensure_order.rb

require "assertions"

A = PolyglotAssertions

original = ArgumentError.new("invalid")
def propagate(error) = raise(error)

captured = begin
  propagate(original)
rescue KeyError
  :wrong
rescue ArgumentError => error
  error
end
A.same(original, captured)
A.truth(captured.is_a?(StandardError))

A.raises(ArgumentError, "invalid") { propagate(original) }
A.raises(ZeroDivisionError) { 1 / 0 }
A.falsey(Exception.new.is_a?(StandardError))

A.done
