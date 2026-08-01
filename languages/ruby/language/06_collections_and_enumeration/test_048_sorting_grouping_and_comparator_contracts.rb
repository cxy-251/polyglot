# frozen_string_literal: true
# polyglot-covers: ruby.collections.sorting-grouping-and-mutation-boundaries

require "assertions"

A = PolyglotAssertions

A.case("sort_by orders keys while explicit input positions provide requested stability") do
  records = [
    {key: 2, name: :second},
    {key: 1, name: :first},
    {key: 2, name: :third}
  ]
  sorted = records.sort_by { |record| record[:key] }
  A.equal([1, 2, 2], sorted.map { |record| record[:key] })

  # Ruby 不承诺 sort/sort_by 稳定；稳定结果必须显式纳入原始位置。
  stable = records.each_with_index.sort_by { |(record, index)| [record[:key], index] }.map(&:first)
  A.equal(%i[first second third], stable.map { |record| record[:name] })
end

A.case("grouping and zipping preserve their documented collection shapes") do
  A.equal({odd: [1, 3], even: [2, 4]}, (1..4).group_by { |value| value.even? ? :even : :odd })
  A.equal([[1, :a], [2, :b]], [1, 2].zip(%i[a b]))
end

A.case("a comparator must return an ordering value") do
  A.raises(ArgumentError) { [1, 2].sort { |_left, _right| nil } }
end

A.case("destructive filters mutate and return their receiver") do
  values = [1, 2, 3]
  returned = values.delete_if(&:odd?)
  A.same(values, returned)
  A.equal([2], values)
end

A.done
