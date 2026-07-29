# frozen_string_literal: true
# polyglot-covers: ruby.errors.throw-catch-is-not-exception

require "assertions"

A = PolyglotAssertions

result = catch(:done) do
  [1, 2, 3].each do |value|
    throw(:done, value * 10) if value == 2
  end
  :unreachable
end

A.equal(20, result)
A.equal(:normal, catch(:unused) { :normal })
error = A.raises(UncaughtThrowError) { throw(:missing, 1) }
A.equal(:missing, error.tag)
A.equal(1, error.value)
A.truth(error.is_a?(StandardError))
A.falsey(UncaughtThrowError == RuntimeError)

A.done
