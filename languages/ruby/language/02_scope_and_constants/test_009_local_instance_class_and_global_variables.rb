# frozen_string_literal: true
# polyglot-covers: ruby.scope.variable-kinds

require "assertions"

A = PolyglotAssertions

$polyglot_ruby_global = :global

class VariableKindsFixture
  @@shared = :class_variable

  def initialize
    @instance = :instance
  end

  def values(local = :local)
    [local, @instance, @@shared, $polyglot_ruby_global]
  end
end

A.equal([:local, :instance, :class_variable, :global], VariableKindsFixture.new.values)
A.includes(global_variables, :$polyglot_ruby_global)

A.done
