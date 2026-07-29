# frozen_string_literal: true
# polyglot-covers: ruby.values.collections-ranges-and-regexp-values

require "assertions"

A = PolyglotAssertions

array = [1, "two", nil]
hash = {one: 1, "two" => 2}
range = 1...4
regexp = /\Aru(?<tail>by)\z/
A.equal(3, array.length)
A.equal(1, hash[:one])
A.equal([1, 2, 3], range.to_a)
A.truth(range.cover?(2.5))
A.equal("by", regexp.match("ruby")[:tail])
A.same(Array, array.class)
A.same(Hash, hash.class)
A.same(Range, range.class)
A.same(Regexp, regexp.class)

A.done
