# frozen_string_literal: true
# polyglot-covers: ruby.calls.method-unbound-method-and-currying

require "assertions"

A = PolyglotAssertions

calculator_class = Class.new do
  def add(left, right)
    left + right
  end
end

A.case("Method binds a receiver while UnboundMethod can rebind only to a compatible object") do
  calculator = calculator_class.new
  bound = calculator.method(:add)
  unbound = bound.unbind
  other = calculator_class.new

  A.equal(5, bound.call(2, 3))
  A.same(calculator, bound.receiver)
  A.equal(9, unbound.bind(other).call(4, 5))
  A.same(calculator_class, unbound.owner)
  A.raises(TypeError) { unbound.bind(Object.new) }
end

A.case("Proc and Method are distinct first-class callable object types") do
  callable = ->(value) { value * 2 }
  bound = calculator_class.new.method(:add)

  A.equal(6, callable.call(3))
  A.same(Proc, callable.class)
  A.same(Method, bound.class)
end

A.case("curry adapts call shape without weakening the original lambda arity") do
  curried = ->(left, right, scale) { (left + right) * scale }.curry
  A.equal(15, curried.call(2).call(3).call(3))
  A.raises(ArgumentError) { ->(left, right) { left + right }.curry(3).call(1, 2, 3) }
end

A.done
