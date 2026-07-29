# frozen_string_literal: true
# polyglot-covers: ruby.values.truthiness-and-nil

require "assertions"

A = PolyglotAssertions

# Ruby 的条件协议只把 false 和 nil 当作假；数值零和空容器并不参与“空值即假”的惯例。
truthy_values = [0, 0.0, "", [], {}, :symbol]
truthy_values.each { |value| A.equal(:truthy, value ? :truthy : :falsey) }
A.equal(:falsey, false ? :truthy : :falsey)
A.equal(:falsey, nil ? :truthy : :falsey)

A.same(NilClass, nil.class)
A.same(TrueClass, true.class)
A.same(FalseClass, false.class)
A.same(Integer, 42.class)
A.same(String, "ruby".class)
A.truth(nil.nil?)
A.falsey(false.nil?)

# `&.` 只短路 nil，不短路 false；这与把二者都视为条件假值是不同的协议。
A.nil_value(nil&.to_s)
A.equal("false", false&.to_s)
A.equal(:fallback, nil || :fallback)
A.equal(:fallback, false || :fallback)
A.equal(0, 0 || :fallback)

A.done
