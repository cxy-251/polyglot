# frozen_string_literal: true
# polyglot-covers: ruby.text.bytes-codepoints-and-graphemes

require "assertions"

A = PolyglotAssertions

text = "e\u0301"
A.equal(3, text.bytesize)
A.equal(2, text.length)
A.equal([101, 769], text.codepoints)
A.equal(["e\u0301"], text.grapheme_clusters)
A.equal("\u00E9", text.unicode_normalize(:nfc))
A.equal(text, "\u00E9".unicode_normalize(:nfd))
A.equal([101, 204, 129], text.bytes)
A.equal("e", text[0])
A.equal("\u0301", text[1])
A.same(Encoding::UTF_8, text.encoding)

A.done
