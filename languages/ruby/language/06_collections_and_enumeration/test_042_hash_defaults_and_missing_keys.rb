# frozen_string_literal: true
# polyglot-covers: ruby.collections.hash-defaults-and-missing-keys

require "assertions"

A = PolyglotAssertions

shared_default = []
shared = Hash.new(shared_default)
shared[:missing] << 1
A.same(shared_default, shared[:other])
A.falsey(shared.key?(:missing))

per_key = Hash.new { |hash, key| hash[key] = [] }
per_key[:one] << 1
A.equal([1], per_key[:one])
A.equal([], per_key[:two])
A.truth(per_key.key?(:two))

plain = {present: nil}
A.truth(plain.key?(:present))
A.falsey(plain.key?(:absent))
A.raises(KeyError) { plain.fetch(:absent) }

A.done
