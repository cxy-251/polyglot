# frozen_string_literal: true
# polyglot-covers: ruby.patterns.alternative-guard-and-pin

require "assertions"

A = PolyglotAssertions

candidate = [:ok, 42]
status_value = case candidate
               in [:ok, Integer] | [:error, Integer]
                 candidate.fetch(1)
               end
A.equal(42, status_value)

guarded = case 6
          in Integer => number if number.even?
            :even_integer
          else
            :other
          end
A.equal(:even_integer, guarded)

expected = 2
pinned = case [1, 2]
         in [1, ^expected]
           :matched
         end
A.equal(:matched, pinned)
A.raises(NoMatchingPatternError) { [1, 3] => [1, ^expected] }

A.done
