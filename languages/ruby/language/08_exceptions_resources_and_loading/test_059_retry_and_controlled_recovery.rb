# frozen_string_literal: true
# polyglot-covers: ruby.errors.retry-and-controlled-recovery

require "assertions"

A = PolyglotAssertions

attempts = 0
result = begin
  attempts += 1
  raise IOError, "transient" if attempts < 3

  :success
rescue IOError
  retry
end

A.equal(:success, result)
A.equal(3, attempts)

nested = begin
  raise KeyError, "missing"
rescue KeyError => error
  [error.class, error.message]
end
A.equal([KeyError, "missing"], nested)

A.done
