# 共同问题：插入删除怎样移动位置，保存的索引和迭代结果何时失效。
# 输入：Array 的 insert、delete_at、元素替换和预先保存索引；观察：位置移动、对象引用及快照策略。
# polyglot-family: collections_and_iteration
# polyglot-concept: sequence_mutation_and_invalidation
# polyglot-related: languages/ruby/language/06_collections_and_enumeration/
# polyglot-related+: test_041_array_indexing_slicing_and_mutation.rb

require "assertions"

A = PolyglotAssertions

values = [+"a", +"b", +"c"]
saved_index = 1
saved_object = values.fetch(saved_index)
values.insert(0, "start")
A.equal("a", values.fetch(saved_index))
A.same(saved_object, values.fetch(2))
A.equal("a", values.delete_at(1))
A.same(saved_object, values.fetch(1))

snapshot = values.dup
values[0] = "changed"
A.equal(["start", "b", "c"], snapshot)
A.equal(["changed", "b", "c"], values)

A.done
