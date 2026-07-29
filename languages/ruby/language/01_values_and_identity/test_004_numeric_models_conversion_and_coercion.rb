# frozen_string_literal: true
# polyglot-covers: ruby.values.numeric-tower-and-conversion

require "assertions"

A = PolyglotAssertions

A.equal(3, 7 / 2)
A.near(3.5, 7.fdiv(2))
A.equal(Rational(1, 2), Rational(2, 4))
A.equal(Complex(1, 2), 1 + 2i)
A.truth(Float::INFINITY.infinite?)
A.truth(Float::NAN.nan?)
A.falsey(Float::NAN == Float::NAN)

# 构造式转换验证完整输入；to_i 是接收者方法，会接受合法前缀并截断小数。
A.equal(255, Integer("ff", 16))
A.equal(3, 3.9.to_i)
A.equal(3, "3x".to_i)
A.raises(ArgumentError) { Integer("3x") }
A.raises(TypeError) { 1 + "2" }

coercible_class = Class.new do
  def initialize(value)
    @value = value
  end

  def coerce(other)
    [other, @value]
  end
end

# 左操作数不认识右操作数时，Numeric 运算会请求右操作数的 coerce 协议。
A.equal(3, 1 + coercible_class.new(2))

A.done
