# frozen_string_literal: true
# polyglot-covers: ruby.values.numeric-tower-and-conversion

require "assertions"

A = PolyglotAssertions

A.case("numeric classes retain distinct division and special-value behavior") do
  A.equal(3, 7 / 2)
  A.near(3.5, 7.fdiv(2))
  A.equal(Rational(1, 2), Rational(2, 4))
  A.equal(Complex(1, 2), 1 + 2i)
  A.truth(Float::INFINITY.infinite?)
  A.truth(Float::NAN.nan?)
  A.falsey(Float::NAN == Float::NAN)
end

A.case("constructors validate complete input while receiver conversions may accept prefixes") do
  A.equal(255, Integer("ff", 16))
  A.equal(3, 3.9.to_i)
  A.equal(3, "3x".to_i)
  A.raises(ArgumentError) { Integer("3x") }
  A.raises(TypeError) { 1 + "2" }
end

coercible_class = Class.new do
  def initialize(value)
    @value = value
  end

  def coerce(other)
    [other, @value]
  end
end

A.case("Numeric operators request coerce when the left operand cannot handle the right") do
  A.equal(3, 1 + coercible_class.new(2))
end

A.done
