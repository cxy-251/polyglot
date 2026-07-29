# frozen_string_literal: true
# polyglot-covers: ruby.objects.class-variables-class-state-and-constants

require "assertions"

A = PolyglotAssertions

class SharedClassStateBase
  @@shared = 1
  @owned = 10
  VALUE = :base

  def self.shared = @@shared

  def self.shared=(value)
    @@shared = value
  end

  def self.owned = @owned
end

class SharedClassStateChild < SharedClassStateBase
  @owned = 20
end

SharedClassStateChild.shared = 2
A.equal(2, SharedClassStateBase.shared)
A.equal(2, SharedClassStateChild.shared)
A.equal(10, SharedClassStateBase.owned)
A.equal(20, SharedClassStateChild.owned)
A.equal(:base, SharedClassStateChild::VALUE)
A.falsey(SharedClassStateChild.const_defined?(:VALUE, false))

A.done
