# frozen_string_literal: true
# polyglot-covers: ruby.c-extension.exception-propagation

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

error = A.raises(ArgumentError, "native failure") do
  PolyglotNative.fail!("native failure")
end
A.equal("native failure", error.message)
A.truth(error.backtrace.first.include?("test_117_c_exception_propagation.rb"))
A.raises(TypeError) { PolyglotNative.fail!(:not_a_string) }

begin
  PolyglotNative.fail!("rescued")
rescue ArgumentError => rescued
  A.equal("rescued", rescued.message)
end

A.done
