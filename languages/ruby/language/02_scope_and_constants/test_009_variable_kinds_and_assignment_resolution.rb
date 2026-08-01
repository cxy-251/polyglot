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

A.case("method bodies distinguish local, instance and class-variable storage") do
  A.equal([:local, :instance, :class_variable], VariableKindsFixture.new.values)
end

receiver = Object.new
def receiver.token = :method

A.case("the parser decides local-variable status from assignment in the static scope") do
  result = receiver.instance_eval do
    before_assignment = token
    token = :local
    [before_assignment, token, self.token]
  end
  A.equal([:method, :local, :method], result)
end

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
A.case("a setter call requires an explicit receiver to differ from local assignment") do
  holder = holder_class.new
  A.equal(:local, holder.assign)
  A.equal(:setter, holder.value)
end

A.done
