# frozen_string_literal: true
# polyglot-covers: ruby.c-extension.blocks-and-callbacks-across-c

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

observed = []
result = PolyglotNative.yield_twice(21) do |value|
  observed << value
  value * observed.length
end
A.equal([21, 21], observed)
A.equal(42, result)
A.raises(ArgumentError, "block required") { PolyglotNative.yield_twice(1) }

receiver = Object.new
receiver.define_singleton_method(:answer) { 42 }
A.equal(42, PolyglotNative.call_ruby(receiver, :answer))
A.raises(NoMethodError) { PolyglotNative.call_ruby(receiver, :missing) }

A.done
