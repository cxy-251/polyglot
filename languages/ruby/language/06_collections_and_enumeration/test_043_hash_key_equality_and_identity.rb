# frozen_string_literal: true
# polyglot-covers: ruby.collections.hash-key-equality-and-identity

require "assertions"

A = PolyglotAssertions

left = +"key"
right = +"key"
value_hash = {left => :value}
A.equal(:value, value_hash[right])
A.falsey(left.equal?(right))
A.truth(value_hash.keys.first.frozen?)

identity_hash = {}.compare_by_identity
identity_hash[left] = :left
A.nil_value(identity_hash[right])
A.equal(:left, identity_hash[left])
A.truth(identity_hash.compare_by_identity?)

A.done
