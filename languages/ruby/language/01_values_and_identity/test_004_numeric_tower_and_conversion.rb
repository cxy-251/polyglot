# frozen_string_literal: true
# polyglot-covers: ruby.values.numeric-tower-and-conversion

require "assertions"

A = PolyglotAssertions

A.equal(4, 2**2)
A.equal(Rational(1, 2), Rational(2, 4))
A.equal(Complex(1, 2), 1 + 2i)
A.equal(3, 7 / 2)
A.near(3.5, 7.fdiv(2))
A.equal(255, Integer("ff", 16))
A.equal(3, 3.9.to_i)
A.raises(ArgumentError) { Integer("3x") }
A.truth(Float::INFINITY.infinite?)
A.truth(Float::NAN.nan?)

A.done
