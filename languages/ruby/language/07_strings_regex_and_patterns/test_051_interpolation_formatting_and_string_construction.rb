# frozen_string_literal: true
# polyglot-covers: ruby.text.interpolation-frozen-literals-and-symbols

require "assertions"

A = PolyglotAssertions

A.case("interpolation, format directives and explicit concatenation choose conversion separately") do
  value = 42
  A.equal("value=42", "value=#{value}")
  A.equal("value=0042", format("value=%04d", value))
  A.equal("value=0042", "value=%04d" % value)
  A.equal("value=42", +"value=" << value.to_s)
end

A.case("ordinary interpolation calls to_s while an explicit inspect expression calls inspect") do
  observed = []
  displayable = Object.new
  displayable.define_singleton_method(:to_s) { observed << :to_s; "shown" }
  displayable.define_singleton_method(:inspect) { observed << :inspect; "debug" }
  A.equal("shown", "#{displayable}")
  A.equal("debug", "#{displayable.inspect}")
  A.equal(%i[to_s inspect], observed)
end

A.case("the frozen-string directive freezes literals while explicit construction stays mutable") do
  literal = "ruby"
  A.truth(literal.frozen?)
  A.raises(FrozenError) { literal << "!" }
  A.equal("ruby!", String.new("ruby") << "!")
end

A.done
