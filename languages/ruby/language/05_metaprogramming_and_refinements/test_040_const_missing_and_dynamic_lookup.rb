# frozen_string_literal: true
# polyglot-covers: ruby.metaprogramming.const-missing-and-dynamic-lookup

require "assertions"

A = PolyglotAssertions

namespace = Module.new do
  class << self
    attr_reader :requested

    def const_missing(name)
      @requested = name
      return const_set(name, 42) if name == :Generated

      super
    end
  end
end

A.equal(42, namespace::Generated)
A.equal(:Generated, namespace.requested)
A.equal(42, namespace::Generated)
A.raises(NameError) { namespace::Unknown }
A.truth(namespace.const_defined?(:Generated, false))
A.equal([:Generated], namespace.constants(false))

A.done
