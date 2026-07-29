# 共同问题：数值和文本怎样格式化、解析和插值。
# 输入：整数、浮点、base、inspect、插值及无效文本；观察：显式协议、精度和错误。
# polyglot-family: text_binary_and_serialization
# polyglot-concept: formatting_parsing_and_interpolation
# polyglot-related: languages/ruby/language/07_strings_regex_and_patterns/
# polyglot-related+: test_051_interpolation_frozen_literals_and_symbols.rb

require "assertions"

A = PolyglotAssertions

A.equal("value=0042", format("value=%04d", 42))
A.equal("3.14", format("%.2f", Math::PI))
A.equal(255, Integer("ff", 16))
A.near(3.5, Float("3.5"))
A.raises(ArgumentError) { Integer("four") }

language = "Ruby"
A.equal("language=Ruby, version=#{RUBY_VERSION}", "language=#{language}, version=#{RUBY_VERSION}")
A.equal('"ruby\\n"', "ruby\n".inspect)
A.equal("42", 42.to_s)

A.done
