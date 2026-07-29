# 共同问题：集合怎样表达成员关系、去重和集合代数。
# 输入：重复标量、不同数值类型、对象身份和 Set 运算；观察：eql?/hash 语义、顺序边界及结果。
# polyglot-family: collections_and_iteration
# polyglot-concept: sets_membership_and_deduplication
# polyglot-related: languages/ruby/language/06_collections_and_enumeration/test_044_set_membership_and_algebra.rb

require "assertions"
require "set"

A = PolyglotAssertions

values = Set[1, 1, 1.0, "a", "a"]
A.equal(3, values.length)
A.truth(values.include?(1))
A.truth(values.include?(1.0))
A.falsey(values.include?(:a))
A.equal(Set[2], Set[1, 2] & Set[2, 3])
A.equal(Set[1, 2, 3], Set[1, 2] | Set[2, 3])
A.equal([1, 2], [1, 1, 2, 1].uniq)

A.done
