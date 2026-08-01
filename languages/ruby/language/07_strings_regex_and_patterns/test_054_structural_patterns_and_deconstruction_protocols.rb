# frozen_string_literal: true
# polyglot-covers: ruby.patterns.array-hash-and-find-patterns

require "assertions"

A = PolyglotAssertions

A.case("array and hash patterns bind selected structure and rest values") do
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
end

class PatternPoint
  def initialize(x, y)
    @x = x
    @y = y
  end

  def deconstruct
    [@x, @y]
  end

  def deconstruct_keys(keys)
    values = {x: @x, y: @y}
    keys ? values.slice(*keys) : values
  end
end

A.case("objects participate through deconstruct and deconstruct_keys protocols") do
  point = PatternPoint.new(3, 4)
  point => [x, y]
  A.equal([3, 4], [x, y])
  point => {x: horizontal, y: vertical}
  A.equal([3, 4], [horizontal, vertical])
  A.raises(NoMatchingPatternError) { point => [0, 0] }
end

A.done
