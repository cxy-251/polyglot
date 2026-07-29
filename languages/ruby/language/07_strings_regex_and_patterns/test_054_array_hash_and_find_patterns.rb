# frozen_string_literal: true
# polyglot-covers: ruby.patterns.array-hash-and-find-patterns

require "assertions"

A = PolyglotAssertions

array_result = case [1, 2, 3]
               in [head, *tail]
                 [head, tail]
               end
A.equal([1, [2, 3]], array_result)

hash_result = case {name: "Ruby", version: 4, stable: true}
              in {name:, **rest}
                [name, rest]
              end
A.equal(["Ruby", {version: 4, stable: true}], hash_result)

find_result = case [0, 1, 2, 3, 4]
              in [*, 2, following, *]
                following
              end
A.equal(3, find_result)

A.done
