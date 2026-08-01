# frozen_string_literal: true
# polyglot-covers: ruby.text.bytes-codepoints-and-graphemes

require "assertions"

A = PolyglotAssertions

A.case("UTF-8 bytes, codepoints and String indexes expose different units") do
  text = "e\u0301"
  A.equal(3, text.bytesize)
  A.equal(2, text.length)
  A.equal([101, 769], text.codepoints)
  A.equal([101, 204, 129], text.bytes)
  A.equal("e", text[0])
  A.equal("\u0301", text[1])
  A.same(Encoding::UTF_8, text.encoding)
end

A.case("grapheme segmentation and normalization are explicit Unicode operations") do
  text = "e\u0301"
  A.equal(["e\u0301"], text.grapheme_clusters)
  A.equal("\u00E9", text.unicode_normalize(:nfc))
  A.equal(text, "\u00E9".unicode_normalize(:nfd))
end

A.done
