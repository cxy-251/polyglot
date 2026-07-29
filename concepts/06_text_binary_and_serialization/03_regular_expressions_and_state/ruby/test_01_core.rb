# 共同问题：正则表达式支持哪些捕获和重复匹配，匹配状态存在哪里。
# 输入：命名捕获、lookaround、scan、MatchData 和 Regexp.last_match；观察：对象化结果与线程局部状态。
# polyglot-family: text_binary_and_serialization
# polyglot-concept: regular_expressions_and_state
# polyglot-related: languages/ruby/language/07_strings_regex_and_patterns/
# polyglot-related+: test_052_regexp_captures_substitution_and_match_state.rb

require "assertions"

A = PolyglotAssertions

match = /(?<name>[a-z]+)-(?<number>\d+)(?=!)/.match("ruby-40!")
A.equal("ruby", match[:name])
A.equal("40", match[:number])
A.equal([0, 7], match.offset(0))
A.equal(["1", "2"], "a1 b2".scan(/\d/))

"ruby" =~ /(ru)(by)/
A.equal("ruby", Regexp.last_match(0))
A.equal("ru", Regexp.last_match(1))
A.nil_value(/x/.match("ruby"))

A.done
