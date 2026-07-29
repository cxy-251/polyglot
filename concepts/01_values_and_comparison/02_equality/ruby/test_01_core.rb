# 共同问题：值相等、哈希相等、对象身份和可定制相等怎样区分。
# 输入：数值、字符串、别名及自定义值；观察：==、eql?、equal?、=== 和 hash 的一致性责任。
# polyglot-family: values_and_comparison
# polyglot-concept: equality
# polyglot-related: languages/ruby/language/01_values_and_identity/test_003_equality_identity_and_hash_keys.rb

require "assertions"

A = PolyglotAssertions

A.truth(1 == 1.0)
A.falsey(1.eql?(1.0))
left = +"ruby"
right = +"ruby"
A.truth(left == right)
A.truth(left.eql?(right))
A.falsey(left.equal?(right))
A.truth(Integer === 42)
A.truth(/uby/ === "ruby")
A.equal(left.hash, right.hash)

A.done
