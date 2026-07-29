# frozen_string_literal: true
# polyglot-covers: ruby.c-extension.array-and-hash-api-boundaries

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

left = Object.new
right = Object.new
pair = PolyglotNative.pair(left, right)
A.equal(2, pair.length)
A.same(left, pair.fetch(0))
A.same(right, pair.fetch(1))

mapping = {ruby: 4, nil => false}
A.equal(4, PolyglotNative.hash_fetch(mapping, :ruby))
A.falsey(PolyglotNative.hash_fetch(mapping, nil))
A.nil_value(PolyglotNative.hash_fetch(mapping, :missing))
A.raises(TypeError) { PolyglotNative.hash_fetch([], :ruby) }

A.done
