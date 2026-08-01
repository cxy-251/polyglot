# frozen_string_literal: true
# polyglot-covers: ruby.calls.return-break-and-next-boundaries

require "assertions"

A = PolyglotAssertions

def proc_nonlocal_return
  callback = proc { return :from_proc }
  callback.call
  :unreachable
end

A.case("return is nonlocal in a Proc but local to a lambda") do
  lambda_return = -> { return :from_lambda }
  A.equal(:from_proc, proc_nonlocal_return)
  A.equal(:from_lambda, lambda_return.call)
end

A.case("break is local to a lambda but requires an active yielding frame in a Proc") do
  lambda_break = -> { break :from_lambda_break }
  A.equal(:from_lambda_break, lambda_break.call)
  A.raises(LocalJumpError) { proc { break :outside }.call }
end

A.case("next supplies the current block invocation result without ending iteration") do
  next_values = [1, 2, 3].map do |value|
    next :skipped if value.even?

    value
  end
  A.equal([1, :skipped, 3], next_values)
end

A.done
