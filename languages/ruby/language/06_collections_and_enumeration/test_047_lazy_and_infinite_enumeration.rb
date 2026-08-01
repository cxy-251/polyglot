# frozen_string_literal: true
# polyglot-covers: ruby.collections.lazy-and-infinite-enumeration

require "assertions"

A = PolyglotAssertions

A.case("lazy transformations evaluate only enough source elements to satisfy demand") do
  observed = []
  lazy_values = (1..).lazy
    .map { |value| observed << value; value * 2 }
    .select { |value| value.odd? || value >= 4 }

  A.equal([4, 6, 8], lazy_values.take(3).force)
  A.equal([1, 2, 3, 4], observed)
end

A.case("finite demand safely bounds cyclic and unbounded lazy sources") do
  cycle = [1, 2].cycle.lazy.take(5)
  A.equal([1, 2, 1, 2, 1], cycle.force)
  A.same(Enumerator::Lazy, (1..3).lazy.class)
end

A.done
