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
A.raises(LocalJumpError) { missing_block_yield }

loose = proc { |left, right| [left, right] }
strict = ->(left, right) { [left, right] }
A.equal([1, nil], loose.call(1))
A.equal([1, 2], loose.call(1, 2, 3))
A.equal([1, 2], loose.call([1, 2]))
A.raises(ArgumentError) { strict.call(1) }
A.raises(ArgumentError) { strict.call(1, 2, 3) }
A.equal([1, 2], strict.call(1, 2))

captured_lambda = capture_block(&strict)
captured_proc = capture_block(&loose)
A.truth(captured_lambda.lambda?)
A.falsey(captured_proc.lambda?)
A.equal(2, captured_lambda.arity)

def strict_method(left, right)
  [left, right]
end
method_proc = method(:strict_method).to_proc
A.truth(method_proc.lambda?)
A.raises(ArgumentError) { method_proc.call(1) }
A.equal([1, 2], method_proc.call(1, 2))

A.done
