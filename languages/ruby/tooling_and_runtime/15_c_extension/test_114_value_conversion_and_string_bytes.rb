# frozen_string_literal: true
# polyglot-covers: ruby.c-extension.value-conversion-and-string-bytes

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

A.equal(42, PolyglotNative.add(19, 23))
A.equal(7, PolyglotNative.add(7.9, 0))
A.raises(TypeError) { PolyglotNative.add("20", 22) }

text = "红宝石"
A.equal(text.bytesize, PolyglotNative.string_bytesize(text))
A.equal(9, PolyglotNative.string_bytesize(text))
A.raises(TypeError) { PolyglotNative.string_bytesize(:ruby) }

A.done
