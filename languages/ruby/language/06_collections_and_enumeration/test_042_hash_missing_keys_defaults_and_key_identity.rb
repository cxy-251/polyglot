# frozen_string_literal: true
# polyglot-covers: ruby.collections.hash-defaults-and-missing-keys

require "assertions"

A = PolyglotAssertions

A.case("an object default is shared and a missing lookup does not insert a key") do
  shared_default = []
  shared = Hash.new(shared_default)
  shared[:missing] << 1
  A.same(shared_default, shared[:other])
  A.falsey(shared.key?(:missing))
end

A.case("a default block can allocate and explicitly store per-key values") do
  per_key = Hash.new { |hash, key| hash[key] = [] }
  per_key[:one] << 1
  A.equal([1], per_key[:one])
  A.equal([], per_key[:two])
  A.truth(per_key.key?(:two))
end

A.case("key? distinguishes present nil from absence while fetch signals absence") do
  plain = {present: nil}
  A.truth(plain.key?(:present))
  A.falsey(plain.key?(:absent))
  A.raises(KeyError) { plain.fetch(:absent) }
end

A.case("ordinary Hash uses value key semantics and freezes its stored String key copy") do
  left = +"key"
  right = +"key"
  value_hash = {left => :value}
  A.equal(:value, value_hash[right])
  A.falsey(left.equal?(right))
  A.truth(value_hash.keys.first.frozen?)
end

A.case("compare_by_identity switches lookup from value equality to object identity") do
  left = +"key"
  right = +"key"
  identity_hash = {}.compare_by_identity
  identity_hash[left] = :left
  A.nil_value(identity_hash[right])
  A.equal(:left, identity_hash[left])
  A.truth(identity_hash.compare_by_identity?)
end

A.done
