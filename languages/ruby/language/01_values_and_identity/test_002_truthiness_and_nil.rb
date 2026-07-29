# frozen_string_literal: true
# polyglot-covers: ruby.values.truthiness-and-nil

require "assertions"

A = PolyglotAssertions

truthy_values = [0, 0.0, "", [], {}, :symbol]
truthy_values.each { |value| A.equal(:truthy, value ? :truthy : :falsey) }
A.equal(:falsey, false ? :truthy : :falsey)
A.equal(:falsey, nil ? :truthy : :falsey)
A.truth(nil.nil?)
A.falsey(false.nil?)

A.done
