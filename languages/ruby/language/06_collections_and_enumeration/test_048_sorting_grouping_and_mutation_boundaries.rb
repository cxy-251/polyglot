# frozen_string_literal: true
# polyglot-covers: ruby.collections.sorting-grouping-and-mutation-boundaries

require "assertions"

A = PolyglotAssertions

records = [
  {key: 2, name: :second},
  {key: 1, name: :first},
  {key: 2, name: :third}
]
sorted = records.sort_by { |record| record[:key] }
A.equal(%i[first second third], sorted.map { |record| record[:name] })
A.equal({odd: [1, 3], even: [2, 4]}, (1..4).group_by { |value| value.even? ? :even : :odd })
A.equal([[1, :a], [2, :b]], [1, 2].zip(%i[a b]))

values = [1, 2, 3]
values.delete_if(&:odd?)
A.equal([2], values)
A.raises(ArgumentError) { [1, 2].sort { |_left, _right| nil } }

A.done
