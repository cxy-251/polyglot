# frozen_string_literal: true
# polyglot-covers: ruby.collections.enumerable-each-protocol

require "assertions"

A = PolyglotAssertions

sequence_class = Class.new do
  include Enumerable

  def initialize(limit)
    @limit = limit
  end

  def each
    return enum_for(__method__) unless block_given?

    1.upto(@limit) { |value| yield value }
  end
end

sequence = sequence_class.new(5)
A.equal([2, 4, 6, 8, 10], sequence.map { |value| value * 2 })
A.equal([2, 4], sequence.select(&:even?))
A.equal(15, sequence.sum)
A.same(Enumerator, sequence.each.class)

A.done
