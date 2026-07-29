# 共同问题：索引原点、负索引、切片区间和越界结果是什么。
# 输入：Array 的整数、Range、start/length、fetch 和 String 索引；观察：0-based、nil 与严格边界。
# polyglot-family: collections_and_iteration
# polyglot-concept: indexing_slicing_and_bounds
# polyglot-related: languages/ruby/language/06_collections_and_enumeration/
# polyglot-related+: test_041_array_indexing_slicing_and_mutation.rb

require "assertions"

A = PolyglotAssertions

values = %w[a b c d]
A.equal("a", values[0])
A.equal("d", values[-1])
A.equal(%w[b c], values[1, 2])
A.equal(%w[b c], values[1..2])
A.nil_value(values[10])
A.equal([], values[4, 2])
A.nil_value(values[5, 0])
A.raises(IndexError) { values.fetch(10) }
A.equal("u", "ruby"[1])

A.done
