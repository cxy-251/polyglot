# frozen_string_literal: true
# polyglot-covers: ruby.values.callable-and-type-objects

require "assertions"

A = PolyglotAssertions

callable = ->(value) { value * 2 }
method_object = "ruby".method(:upcase)
anonymous_class = Class.new { def answer = 42 }
anonymous_module = Module.new { def label = :mixed_in }
A.equal(6, callable.call(3))
A.equal("RUBY", method_object.call)
A.equal(42, anonymous_class.new.answer)
anonymous_class.include(anonymous_module)
A.equal(:mixed_in, anonymous_class.new.label)
A.same(Proc, callable.class)
A.same(Method, method_object.class)
A.truth(anonymous_class.is_a?(Class))
A.truth(anonymous_module.is_a?(Module))

A.done
