# frozen_string_literal: true
# polyglot-covers: ruby.calls.splat-and-array-conversion

require "assertions"

A = PolyglotAssertions

convertible = Object.new
def convertible.to_a = [2, 3]

def positional_sum(*values)
  values.sum
end

A.equal(6, positional_sum(1, *[2, 3]))
A.equal([1, 2, 3, 4], [1, *convertible, 4])
A.equal([], [*nil])
A.equal([:value], [*:value])
A.raises(TypeError) { positional_sum(*Object.new) }

A.done
