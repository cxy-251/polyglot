# frozen_string_literal: true
# polyglot-covers: ruby.scope.nested-scope-and-shadowing

require "assertions"

A = PolyglotAssertions

A.case("block parameters and semicolon locals shadow outer bindings") do
  shared = 1
  shadowed = 10
  outside_only = :outside
  result = [2].map do |shadowed; outside_only|
    shared += shadowed
    outside_only = shadowed * 10
    [shared, outside_only]
  end

  A.equal([[3, 20]], result)
  A.equal(3, shared)
  A.equal(10, shadowed)
  A.equal(:outside, outside_only)
  A.raises(NameError) { eval("outside_only_from_block", binding) }
end

A.case("ordinary outer locals are captured and assignment updates the shared slot") do
  captured = :outer
  1.times { captured = :changed }
  A.equal(:changed, captured)
end

A.done
