# frozen_string_literal: true
# polyglot-covers: ruby.patterns.alternative-guard-and-pin

require "assertions"

A = PolyglotAssertions

A.case("alternative patterns accept either structural branch") do
  candidate = [:ok, 42]
  status_value = case candidate
                 in [:ok, Integer] | [:error, Integer]
                   candidate.fetch(1)
                 end
  A.equal(42, status_value)
end

A.case("a guard applies after structural matching and may use the bound value") do
  guarded = case 6
            in Integer => number if number.even?
              :even_integer
            else
              :other
            end
  A.equal(:even_integer, guarded)
end

A.case("pin compares against an existing local instead of rebinding it") do
  expected = 2
  pinned = case [1, 2]
           in [1, ^expected]
             :matched
           end
  A.equal(:matched, pinned)
  A.raises(NoMatchingPatternError) { [1, 3] => [1, ^expected] }
end

A.done
