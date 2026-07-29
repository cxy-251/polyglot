# 共同问题：语言提供哪些数值模型，显式和隐式转换在哪里发生。
# 输入：整数、浮点、Rational、Complex、文本和无效值；观察：运算结果、精度、解析与失败。
# polyglot-family: values_and_comparison
# polyglot-concept: numeric_models_and_conversion
# polyglot-related: languages/ruby/language/01_values_and_identity/test_004_numeric_models_conversion_and_coercion.rb

require "assertions"

A = PolyglotAssertions

A.same(Integer, (2**100).class)
A.equal(3, 7 / 2)
A.near(3.5, 7.fdiv(2))
A.equal(Rational(1, 3), Rational(2, 6))
A.equal(Complex(1, 2), 1 + 2i)
A.equal(255, Integer("ff", 16))
A.equal(3, 3.9.to_i)
A.raises(ArgumentError) { Integer("3x") }
A.truth(Float::INFINITY.infinite?)
A.truth(Float::NAN.nan?)

A.done
