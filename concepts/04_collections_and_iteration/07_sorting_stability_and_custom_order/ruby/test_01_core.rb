# 共同问题：排序稳定性如何界定，自定义次序怎样写成完整严格顺序。
# 输入：重复主键、原始位置、sort_by 和 sort!；观察：稳定性不保证、显式 tie-breaker 及原地返回值。
# polyglot-family: collections_and_iteration
# polyglot-concept: sorting_stability_and_custom_order
# polyglot-related: languages/ruby/language/06_collections_and_enumeration/
# polyglot-related+: test_048_sorting_grouping_and_mutation_boundaries.rb

require "assertions"

A = PolyglotAssertions

records = [
  {key: 1, position: 2},
  {key: 1, position: 1},
  {key: 0, position: 3}
]
ordered = records.sort_by { |record| [record.fetch(:key), record.fetch(:position)] }
A.equal([3, 1, 2], ordered.map { _1.fetch(:position) })

values = [3, 1, 2]
A.same(values, values.sort!)
A.equal([1, 2, 3], values)
A.equal([3, 2, 1], values.sort { |left, right| right <=> left })

A.done
