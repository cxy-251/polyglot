# frozen_string_literal: true
# polyglot-covers: ruby.calls.return-break-and-next-boundaries

require "assertions"

A = PolyglotAssertions

def proc_nonlocal_return
  callback = proc { return :from_proc }
  callback.call
  :unreachable
end

lambda_return = -> { return :from_lambda }
lambda_break = -> { break :from_lambda_break }
next_values = [1, 2, 3].map do |value|
  next :skipped if value.even?

  value
end

A.equal(:from_proc, proc_nonlocal_return)
A.equal(:from_lambda, lambda_return.call)
A.equal(:from_lambda_break, lambda_break.call)
A.equal([1, :skipped, 3], next_values)
A.raises(LocalJumpError) { proc { break :outside }.call }

A.done
