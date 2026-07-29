# 共同问题：哪些值可排序，Hash 键使用哪套相等与哈希协议。
# 输入：数值、字符串、自定义键、NaN 和不可比较对象；观察：<=>、sort、eql?/hash 及键身份。
# polyglot-family: values_and_comparison
# polyglot-concept: ordering_hashing_and_key_semantics
# polyglot-related: languages/ruby/language/01_values_and_identity/test_003_equality_identity_and_case_equality.rb

require "assertions"

A = PolyglotAssertions

A.equal(-1, 1 <=> 2)
A.equal(["a", "b"], ["b", "a"].sort)
A.nil_value(Object.new <=> Object.new)
A.raises(ArgumentError) { [1, "1"].sort }

mapping = {1 => :integer, 1.0 => :float}
A.equal(2, mapping.length)
A.equal(:integer, mapping[1])
A.equal(:float, mapping[1.0])

nan = Float::NAN
A.falsey(nan == nan)
A.truth({nan => :present}.key?(nan))

A.done
