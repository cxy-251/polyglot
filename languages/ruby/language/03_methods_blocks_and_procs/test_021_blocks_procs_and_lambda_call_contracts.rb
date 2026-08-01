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

A.case("yield observes block presence and raises when no block exists") do
  A.equal(:no_block, invoke_with_yield(2))
  A.equal(6, invoke_with_yield(2) { |value| value * 3 })
  A.raises(LocalJumpError) { missing_block_yield }
end

A.case("non-lambda Proc arguments are loose while lambda arguments are method-like") do
  loose = proc { |left, right| [left, right] }
  strict = ->(left, right) { [left, right] }

  A.equal([1, nil], loose.call(1))
  A.equal([1, 2], loose.call(1, 2, 3))
  A.equal([1, 2], loose.call([1, 2]))
  A.raises(ArgumentError) { strict.call(1) }
  A.raises(ArgumentError) { strict.call(1, 2, 3) }
  A.equal([1, 2], strict.call(1, 2))
end

A.case("explicit block capture preserves lambda identity and arity") do
  captured_lambda = capture_block(&->(left, right) { [left, right] })
  captured_proc = capture_block(&proc { |left, right| [left, right] })
  A.truth(captured_lambda.lambda?)
  A.falsey(captured_proc.lambda?)
  A.equal(2, captured_lambda.arity)
end

def strict_method(left, right)
  [left, right]
end
A.case("Method#to_proc produces a strict lambda-style callable") do
  method_proc = method(:strict_method).to_proc
  A.truth(method_proc.lambda?)
  A.raises(ArgumentError) { method_proc.call(1) }
  A.equal([1, 2], method_proc.call(1, 2))
end

A.done
