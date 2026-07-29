# frozen_string_literal: true
# polyglot-covers: ruby.scope.setter-requires-explicit-receiver

require "assertions"

A = PolyglotAssertions

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
