# frozen_string_literal: true
# polyglot-covers: ruby.scope.lexical-constant-lookup

require "assertions"

A = PolyglotAssertions

module LexicalOuter
  VALUE = :outer

  module Inner
    class Nested
      def self.lexical_value
        VALUE
      end
    end
  end
end

A.equal(:outer, LexicalOuter::Inner::Nested.lexical_value)
A.equal(LexicalOuter::Inner, LexicalOuter.const_get(:Inner, false))
A.raises(NameError) { LexicalOuter::Inner.const_get(:VALUE, false) }

A.done
