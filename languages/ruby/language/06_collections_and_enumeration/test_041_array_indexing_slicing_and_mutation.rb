# frozen_string_literal: true
# polyglot-covers: ruby.collections.array-indexing-slicing-and-mutation

require "assertions"

A = PolyglotAssertions

values = [10, 20, 30, 40]
A.equal(10, values[0])
A.equal(40, values[-1])
A.nil_value(values[10])
A.equal([20, 30], values[1, 2])
A.equal([20, 30], values[1..2])
A.equal([], values[4, 2])
A.nil_value(values[5, 0])
values[1, 2] = [:replacement]
A.equal([10, :replacement, 40], values)

A.done
