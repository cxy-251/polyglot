# 共同问题：可调用对象怎样绑定 receiver，脱离属性后是否仍保留调用上下文。
# 输入：Method、UnboundMethod、Proc 和自定义 call；观察：self 绑定、bind 约束及调用协议。
# polyglot-family: functions_and_calls
# polyglot-concept: callable_binding_and_invocation_context
# polyglot-related: languages/ruby/language/03_methods_blocks_and_procs/test_024_method_unbound_method_and_currying.rb

require "assertions"

A = PolyglotAssertions

klass = Class.new do
  def initialize(value) = @value = value
  def read = @value
end
first = klass.new(1)
second = klass.new(2)
bound = first.method(:read)
A.equal(1, bound.call)
A.same(first, bound.receiver)
A.equal(2, klass.instance_method(:read).bind(second).call)
A.raises(TypeError) { klass.instance_method(:read).bind(Object.new) }

callable = Object.new
callable.define_singleton_method(:call) { |value| value * 2 }
A.equal(6, callable.call(3))

A.done
