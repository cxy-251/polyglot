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

increment, current = factory.call(10)
A.equal(11, increment.call)
A.equal(11, current.call)
A.equal(12, increment.call)
A.equal(12, current.call)

other_increment, other_current = factory.call(0)
A.equal(1, other_increment.call)
A.equal(1, other_current.call)
A.equal(12, current.call)

A.done
