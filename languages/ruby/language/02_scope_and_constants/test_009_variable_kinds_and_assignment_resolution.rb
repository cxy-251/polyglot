# frozen_string_literal: true
# polyglot-covers: ruby.scope.variable-kinds

require "assertions"

A = PolyglotAssertions

class VariableKindsFixture
  @@shared = :class_variable

  def initialize
    @instance = :instance
  end

  def values(local = :local)
    [local, @instance, @@shared]
  end
end

A.equal([:local, :instance, :class_variable], VariableKindsFixture.new.values)

receiver = Object.new
def receiver.token = :method

result = receiver.instance_eval do
  before_assignment = token
  token = :local
  [before_assignment, token, self.token]
end
A.equal([:method, :local, :method], result)

holder_class = Class.new do
  attr_reader :value

  def value=(new_value)
    @value = new_value
  end

  def assign
    value = :local
    self.value = :setter
    value
  end
end
holder = holder_class.new
A.equal(:local, holder.assign)
A.equal(:setter, holder.value)

A.done
