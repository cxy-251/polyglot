# frozen_string_literal: true
# polyglot-covers: ruby.collections.set-membership-and-algebra

require "assertions"
require "set"

A = PolyglotAssertions

values = Set[1, 2, 2, 3]
A.equal(3, values.size)
A.truth(values.include?(2))
A.equal(Set[2, 3], values & Set[2, 3, 4])
A.equal(Set[1, 2, 3, 4], values | Set[4])
A.equal(Set[1], values - Set[2, 3])
A.truth(Set[1, 2].subset?(values))
A.equal([1, 2, 3], values.to_a.sort)

A.done
