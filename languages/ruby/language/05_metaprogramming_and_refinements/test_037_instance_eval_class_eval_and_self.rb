# frozen_string_literal: true
# polyglot-covers: ruby.metaprogramming.instance-eval-class-eval-and-self

require "assertions"

A = PolyglotAssertions

object = Object.new
observed_self = object.instance_eval { self }
A.same(object, observed_self)
object.instance_eval { @value = 42 }
A.equal(42, object.instance_variable_get(:@value))

generated_class = Class.new
generated_class.class_eval do
  def instance_value
    :instance
  end
end
generated_class.instance_eval do
  def class_value
    :class
  end
end

A.equal(:instance, generated_class.new.instance_value)
A.equal(:class, generated_class.class_value)
A.falsey(generated_class.new.respond_to?(:class_value))

A.done
