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

A.case("lexical constant lookup can find an outer binding absent from the inner table") do
  A.equal(:outer, LexicalOuter::Inner::Nested.lexical_value)
  A.raises(NameError) { LexicalOuter::Inner.const_get(:VALUE, false) }
end

class ClassStateBaseFixture
  @@shared = 1
  @owned = 10
  VALUE = :base

  def self.shared = @@shared

  def self.shared=(value)
    @@shared = value
  end

  def self.owned = @owned
end

class ClassStateChildFixture < ClassStateBaseFixture
  @owned = 20
end

A.case("class variables are shared while class-instance variables are owned") do
  ClassStateChildFixture.shared = 2
  A.equal([2, 2], [ClassStateBaseFixture.shared, ClassStateChildFixture.shared])
  A.equal([10, 20], [ClassStateBaseFixture.owned, ClassStateChildFixture.owned])
  A.equal(:base, ClassStateChildFixture::VALUE)
  A.falsey(ClassStateChildFixture.const_defined?(:VALUE, false))
end

A.case("module assignment aliases the namespace and its mutable constant value") do
  exports = Module.new
  exports.const_set(:ITEMS, [])
  module_alias = exports
  module_alias::ITEMS << :ruby

  A.same(exports, module_alias)
  A.same(exports::ITEMS, module_alias::ITEMS)
  A.equal([:ruby], exports::ITEMS)
end

namespace = Module.new do
  def self.const_missing(name)
    return const_set(name, 42) if name == :Generated

    super
  end
end
A.case("const_missing may install a binding but must delegate unknown names") do
  A.equal(42, namespace::Generated)
  A.equal(42, namespace::Generated)
  A.raises(NameError) { namespace::Unknown }
end

A.done
