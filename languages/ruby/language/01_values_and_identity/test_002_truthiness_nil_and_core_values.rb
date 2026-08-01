# frozen_string_literal: true
# polyglot-covers: ruby.values.truthiness-and-nil

require "assertions"

A = PolyglotAssertions

A.case("only false and nil are falsey in condition positions") do
  # 数值零和空容器不参与“空值即假”的惯例。
  truthy_values = [0, 0.0, "", [], {}, :symbol]
  truthy_values.each { |value| A.equal(:truthy, value ? :truthy : :falsey) }
  A.equal(:falsey, false ? :truthy : :falsey)
  A.equal(:falsey, nil ? :truthy : :falsey)
end

A.case("core literal values have distinct classes and nil? is narrow") do
  A.same(NilClass, nil.class)
  A.same(TrueClass, true.class)
  A.same(FalseClass, false.class)
  A.same(Integer, 42.class)
  A.same(String, "ruby".class)
  A.truth(nil.nil?)
  A.falsey(false.nil?)
end

A.case("safe navigation only short-circuits nil while || follows truthiness") do
  A.nil_value(nil&.to_s)
  A.equal("false", false&.to_s)
  A.equal(:fallback, nil || :fallback)
  A.equal(:fallback, false || :fallback)
  A.equal(0, 0 || :fallback)
end

A.done
