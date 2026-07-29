# frozen_string_literal: true
# polyglot-covers: ruby.scope.block-local-variables

require "assertions"

A = PolyglotAssertions

shared = 1
block_local = :outside
result = [2].map do |value; block_local|
  shared += value
  block_local = value * 10
  [shared, block_local]
end

A.equal([[3, 20]], result)
A.equal(3, shared)
A.equal(:outside, block_local)
A.raises(NameError) { eval("value", binding) }

A.done
