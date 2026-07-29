# frozen_string_literal: true
# polyglot-covers: ruby.calls.yield-and-block-objects

require "assertions"

A = PolyglotAssertions

def invoke_with_yield(value)
  return :no_block unless block_given?

  yield(value)
end

def capture_block(&block)
  block
end

def missing_block_yield
  yield
end

A.equal(:no_block, invoke_with_yield(2))
A.equal(6, invoke_with_yield(2) { |value| value * 3 })
captured = capture_block { |value| value + 1 }
A.same(Proc, captured.class)
A.equal(4, captured.call(3))
A.raises(LocalJumpError) { missing_block_yield }

A.done
