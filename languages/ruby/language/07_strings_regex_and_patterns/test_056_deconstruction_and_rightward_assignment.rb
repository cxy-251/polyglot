# frozen_string_literal: true
# polyglot-covers: ruby.patterns.deconstruction-and-rightward-assignment

require "assertions"

A = PolyglotAssertions

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

point = PatternPoint.new(3, 4)
point => [x, y]
A.equal([3, 4], [x, y])

point => {x: horizontal, y: vertical}
A.equal([3, 4], [horizontal, vertical])
A.raises(NoMatchingPatternError) { point => [0, 0] }

A.done
