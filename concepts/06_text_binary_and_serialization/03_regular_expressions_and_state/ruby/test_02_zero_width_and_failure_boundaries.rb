# 共同问题：零宽匹配怎样前进，无效 pattern 和替换 callback 失败怎样传播。
# 输入：anchors、lookahead、空 pattern、无效源码和 gsub block；观察：有限迭代、RegexpError 与原异常。
# polyglot-family: text_binary_and_serialization
# polyglot-concept: regular_expressions_and_state
# polyglot-related: languages/ruby/language/07_strings_regex_and_patterns/
# polyglot-related+: test_052_regexp_captures_substitution_and_match_state.rb

require "assertions"

A = PolyglotAssertions

A.equal(["", "", ""], "ab".scan(//))
A.equal(["", ""], "ab".scan(/(?=[ab])/))
A.equal("XaXbX", "ab".gsub(//, "X"))
A.raises(RegexpError) { Regexp.new("[") }

error = RuntimeError.new("replacement")
captured = A.raises(RuntimeError, "replacement") do
  "a1".gsub(/\d/) { raise error }
end
A.same(error, captured)

A.done
