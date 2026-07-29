# frozen_string_literal: true
# polyglot-covers: ruby.calls.method-unbound-method-and-currying

require "assertions"

A = PolyglotAssertions

calculator_class = Class.new do
  def add(left, right)
    left + right
  end
end

calculator = calculator_class.new
bound = calculator.method(:add)
unbound = bound.unbind
other = calculator_class.new

A.equal(5, bound.call(2, 3))
A.same(calculator, bound.receiver)
A.equal(9, unbound.bind(other).call(4, 5))
A.same(calculator_class, unbound.owner)
A.raises(TypeError) { unbound.bind(Object.new) }

callable = ->(value) { value * 2 }
A.equal(6, callable.call(3))
A.same(Proc, callable.class)
A.same(Method, bound.class)

curried = ->(left, right, scale) { (left + right) * scale }.curry
A.equal(15, curried.call(2).call(3).call(3))
# curry 只适配调用形状；原 lambda 的严格 arity 仍可在指定目标 arity 时暴露错误。
A.raises(ArgumentError) { ->(left, right) { left + right }.curry(3).call(1, 2, 3) }

A.done
