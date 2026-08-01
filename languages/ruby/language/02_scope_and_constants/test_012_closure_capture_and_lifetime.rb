# frozen_string_literal: true
# polyglot-covers: ruby.scope.closure-capture-and-lifetime

require "assertions"

A = PolyglotAssertions

factory = lambda do |initial|
  value = initial
  [
    -> { value += 1 },
    -> { value }
  ]
end

A.case("closures returned together retain one mutable lexical slot") do
  increment, current = factory.call(10)
  A.equal(11, increment.call)
  A.equal(11, current.call)
  A.equal(12, increment.call)
  A.equal(12, current.call)
end

A.case("separate factory calls allocate independent captured environments") do
  first_increment, first_current = factory.call(10)
  other_increment, other_current = factory.call(0)

  A.equal(1, other_increment.call)
  A.equal(1, other_current.call)
  A.equal(11, first_increment.call)
  A.equal(11, first_current.call)
end

A.done
