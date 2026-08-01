# frozen_string_literal: true
# polyglot-covers: ruby.objects.construction-allocation-and-inheritance

require "assertions"

A = PolyglotAssertions

base = Class.new do
  def initialize(value)
    @value = value
  end

  attr_reader :value

  def describe(suffix: "base")
    "#{value}:#{suffix}"
  end
end

child = Class.new(base) do
  def describe(suffix: "child")
    "child(#{super})"
  end
end

A.case("allocate creates an instance without running initialize") do
  allocated = child.allocate
  A.truth(allocated.is_a?(child))
  A.nil_value(allocated.value)
end

A.case("new initializes inherited state and super forwards the explicit keyword") do
  initialized = child.new(42)
  A.equal(42, initialized.value)
  A.equal("child(42:child)", initialized.describe)
  A.equal("child(42:custom)", initialized.describe(suffix: "custom"))
  A.same(base, child.superclass)
  A.equal([child, base], child.ancestors.take(2))
end

A.done
