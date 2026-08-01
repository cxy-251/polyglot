# frozen_string_literal: true
# polyglot-covers: ruby.c-extension.value-conversion-and-string-bytes

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

A.case("native numeric conversion follows the fixture's Integer coercion and type checks") do
  A.equal(42, PolyglotNative.add(19, 23))
  A.equal(7, PolyglotNative.add(7.9, 0))
  A.raises(TypeError) { PolyglotNative.add("20", 22) }
end

A.case("native String access counts encoded bytes and rejects non-String values") do
  text = "红宝石"
  A.equal(text.bytesize, PolyglotNative.string_bytesize(text))
  A.equal(9, PolyglotNative.string_bytesize(text))
  A.raises(TypeError) { PolyglotNative.string_bytesize(:ruby) }
end

A.case("native Array construction preserves Ruby object identities") do
  left = Object.new
  right = Object.new
  pair = PolyglotNative.pair(left, right)
  A.same(left, pair.fetch(0))
  A.same(right, pair.fetch(1))
end

A.case("native Hash lookup distinguishes false, nil result and invalid receiver type") do
  mapping = {ruby: 4, nil => false}
  A.equal(4, PolyglotNative.hash_fetch(mapping, :ruby))
  A.falsey(PolyglotNative.hash_fetch(mapping, nil))
  A.nil_value(PolyglotNative.hash_fetch(mapping, :missing))
  A.raises(TypeError) { PolyglotNative.hash_fetch([], :ruby) }
end

A.case("a C-defined method has no Ruby source location") do
  A.nil_value(PolyglotNative.method(:add).source_location)
end
A.done
