# 共同问题：子集合是否共享底层存储，结构变化会不会令 view 失效。
# 输入：Array alias、slice、嵌套对象和 source 突变；观察：Ruby slice 为浅复制而非原生 view。
# polyglot-family: collections_and_iteration
# polyglot-concept: sequence_mutation_and_invalidation
# polyglot-related: languages/ruby/language/06_collections_and_enumeration/
# polyglot-related+: test_041_array_indexing_slicing_and_mutation.rb

require "assertions"

A = PolyglotAssertions

nested = +"shared"
source = [nested, "middle", "end"]
alias_value = source
slice = source[0, 2]
alias_value << "new"
A.equal(4, source.length)
A.equal(2, slice.length)
A.falsey(slice.equal?(source))
A.same(nested, slice.first)

nested << "-changed"
A.equal("shared-changed", source.first)
A.equal("shared-changed", slice.first)
source.delete_at(1)
A.equal(["shared-changed", "middle"], slice)

A.done
