# frozen_string_literal: true
# polyglot-covers: ruby.metaprogramming.define-method-and-singleton-method

require "assertions"

A = PolyglotAssertions

factor = 3
generated_class = Class.new do
  define_method(:scale) { |value| value * factor }
end

object = generated_class.new
object.define_singleton_method(:label) { :singleton }

A.equal(12, object.scale(4))
A.equal(:singleton, object.label)
A.falsey(generated_class.new.respond_to?(:label))
A.same(generated_class, object.method(:scale).owner)
A.same(object.singleton_class, object.method(:label).owner)
A.equal([[:req, :value]], object.method(:scale).parameters)

A.done
