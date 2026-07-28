# frozen_string_literal: true
# polyglot-covers: ruby.values.runtime-and-core-objects

require "assertions"

A = PolyglotAssertions

A.equal("4.0.6", RUBY_VERSION)
A.equal("ruby", RUBY_ENGINE)
A.same(NilClass, nil.class)
A.same(TrueClass, true.class)
A.same(FalseClass, false.class)
A.same(Integer, 42.class)
A.same(String, "ruby".class)
A.same(Object, Object.new.class)

A.done
