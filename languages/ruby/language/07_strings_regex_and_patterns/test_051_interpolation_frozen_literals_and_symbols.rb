# frozen_string_literal: true
# polyglot-covers: ruby.text.interpolation-frozen-literals-and-symbols

require "assertions"

A = PolyglotAssertions

value = 42
literal = "ruby"
interpolated = "value=#{value}"
mutable = String.new("ruby")

A.equal("value=42", interpolated)
A.truth(literal.frozen?)
A.raises(FrozenError) { literal << "!" }
mutable << "!"
A.equal("ruby!", mutable)
A.truth(:ruby.equal?(:ruby))
A.equal("ruby", :ruby.name)
A.truth("ruby".to_sym.equal?(:ruby))

A.done
