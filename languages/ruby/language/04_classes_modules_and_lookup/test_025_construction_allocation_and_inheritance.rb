# frozen_string_literal: true
# polyglot-covers: ruby.objects.construction-allocation-and-inheritance

require "assertions"

A = PolyglotAssertions

class ConstructionBase
  def initialize(value)
    @value = value
  end

  attr_reader :value
end

class ConstructionChild < ConstructionBase
end

allocated = ConstructionChild.allocate
A.truth(allocated.is_a?(ConstructionChild))
A.nil_value(allocated.value)

initialized = ConstructionChild.new(42)
A.equal(42, initialized.value)
A.same(ConstructionBase, ConstructionChild.superclass)
A.truth(ConstructionBase === initialized)
A.equal([ConstructionChild, ConstructionBase], ConstructionChild.ancestors.take(2))

A.done
