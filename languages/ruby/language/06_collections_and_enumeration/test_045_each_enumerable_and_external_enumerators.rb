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
    :completed
  end
end

sequence = sequence_class.new(5)
A.equal([2, 4, 6, 8, 10], sequence.map { |value| value * 2 })
A.equal([2, 4], sequence.select(&:even?))
A.equal(15, sequence.sum)

enumerator = sequence.each
A.same(Enumerator, enumerator.class)
A.equal(1, enumerator.peek)
A.equal(1, enumerator.next)
A.equal([2, 3, 4, 5], 4.times.map { enumerator.next })
finished = A.raises(StopIteration) { enumerator.next }
A.equal(:completed, finished.result)
enumerator.rewind
A.equal(1, enumerator.next)

produced = Enumerator.new do |output|
  output << 10
  output.yield(20)
  :producer_result
end
A.equal([10, 20], produced.to_a)

A.done
