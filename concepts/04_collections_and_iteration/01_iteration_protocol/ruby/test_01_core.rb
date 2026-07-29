# 共同问题：普通集合迭代由什么协议驱动，回调收到哪些值。
# 输入：Array、Hash、Range 和 each；观察：yield 形状、插入顺序及 Enumerable 对 each 的依赖。
# polyglot-family: collections_and_iteration
# polyglot-concept: iteration_protocol
# polyglot-related: languages/ruby/language/06_collections_and_enumeration/
# polyglot-related+: test_045_each_enumerable_and_external_enumerators.rb

require "assertions"

A = PolyglotAssertions

values = []
returned = [1, 2, 3].each { |value| values << value * 2 }
A.equal([2, 4, 6], values)
A.equal([1, 2, 3], returned)

pairs = []
{a: 1, b: 2}.each { |key, value| pairs << [key, value] }
A.equal([[:a, 1], [:b, 2]], pairs)
A.equal([1, 2, 3], (1..3).to_a)

A.done
