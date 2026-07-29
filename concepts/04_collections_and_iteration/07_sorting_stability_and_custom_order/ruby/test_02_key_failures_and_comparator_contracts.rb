# 共同问题：key/comparator 失败和不完整比较关系怎样暴露。
# 输入：缺失字段、mixed 类型、抛错 comparator 和副作用；观察：异常立即传播且不承诺部分结果。
# polyglot-family: collections_and_iteration
# polyglot-concept: sorting_stability_and_custom_order
# polyglot-related: languages/ruby/language/06_collections_and_enumeration/
# polyglot-related+: test_048_sorting_grouping_and_mutation_boundaries.rb

require "assertions"

A = PolyglotAssertions

A.raises(KeyError) { [{key: 1}, {}].sort_by { _1.fetch(:key) } }
A.raises(ArgumentError) { [1, "2"].sort }

calls = 0
error = A.raises(RuntimeError, "comparator failed") do
  [3, 2, 1].sort do |left, right|
    calls += 1
    raise "comparator failed" if calls == 2

    left <=> right
  end
end
A.equal("comparator failed", error.message)
A.equal(2, calls)

A.done
