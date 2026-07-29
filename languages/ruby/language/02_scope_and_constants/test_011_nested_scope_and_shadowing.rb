# frozen_string_literal: true
# polyglot-covers: ruby.scope.nested-scope-and-shadowing

require "assertions"

A = PolyglotAssertions

value = :outer
result = lambda do
  value = :block
  inner = lambda do
    value = :inner
    value
  end
  [inner.call, value]
end.call

A.equal([:inner, :inner], result)
A.equal(:inner, value)

shadowed = 10
1.times do |shadowed; block_only|
  shadowed = 20
  block_only = 30
  A.equal([20, 30], [shadowed, block_only])
end
A.equal(10, shadowed)

A.done
