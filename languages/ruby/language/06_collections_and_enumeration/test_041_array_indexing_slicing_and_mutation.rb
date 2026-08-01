# frozen_string_literal: true
# polyglot-covers: ruby.collections.array-indexing-slicing-and-mutation

require "assertions"

A = PolyglotAssertions

A.case("single-element indexing supports negative offsets and returns nil out of range") do
  values = [10, 20, 30, 40]
  A.equal(10, values[0])
  A.equal(40, values[-1])
  A.nil_value(values[10])
end

A.case("slice indexing distinguishes an empty slice at the end from a start beyond it") do
  values = [10, 20, 30, 40]
  A.equal([20, 30], values[1, 2])
  A.equal([20, 30], values[1..2])
  A.equal([], values[4, 2])
  A.nil_value(values[5, 0])
end

A.case("slice assignment may replace several elements with a differently sized sequence") do
  values = [10, 20, 30, 40]
  values[1, 2] = [:replacement]
  A.equal([10, :replacement, 40], values)
end

A.done
