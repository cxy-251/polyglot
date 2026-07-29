# 共同问题：程序员契约和可恢复操作失败怎样发出信号。
# 输入：raise、参数验证、nil/错误二元协议和 rescue；观察：异常类、消息及显式结果协议。
# polyglot-family: errors_and_resources
# polyglot-concept: contracts_assertions_and_failure_signaling
# polyglot-related: languages/ruby/language/08_exceptions_resources_and_loading/test_057_rescue_else_ensure_order.rb

require "assertions"

A = PolyglotAssertions

def positive(value)
  raise ArgumentError, "must be positive" unless value.positive?

  value
end

A.equal(2, positive(2))
A.raises(ArgumentError, "must be positive") { positive(0) }

def lookup(mapping, key)
  return [mapping.fetch(key), nil] if mapping.key?(key)

  [nil, KeyError.new("missing #{key}")]
end

A.equal([1, nil], lookup({a: 1}, :a))
value, error = lookup({}, :a)
A.nil_value(value)
A.same(KeyError, error.class)

A.done
