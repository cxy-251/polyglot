# frozen_string_literal: true
# polyglot-covers: ruby.c-extension.blocks-and-callbacks-across-c

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

A.case("rb_yield re-enters a Ruby block and propagates the final block result") do
  observed = []
  result = PolyglotNative.yield_twice(21) do |value|
    observed << value
    value * observed.length
  end
  A.equal([21, 21], observed)
  A.equal(42, result)
  A.raises(ArgumentError, "block required") { PolyglotNative.yield_twice(1) }
end

A.case("rb_funcall uses ordinary Ruby dispatch and propagates a missing method") do
  receiver = Object.new
  receiver.define_singleton_method(:answer) { 42 }
  A.equal(42, PolyglotNative.call_ruby(receiver, :answer))
  A.raises(NoMethodError) { PolyglotNative.call_ruby(receiver, :missing) }
end

A.case("rb_raise crosses the C frame with its class, message and argument checks") do
  error = A.raises(ArgumentError, "native failure") do
    PolyglotNative.fail!("native failure")
  end
  A.equal("native failure", error.message)
  A.raises(TypeError) { PolyglotNative.fail!(:not_a_string) }
end
A.done
