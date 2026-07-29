# 共同问题：字符串长度和索引单位是 byte、code point 还是 grapheme cluster。
# 输入：ASCII、组合字符、emoji 和 NUL；观察：bytesize、length、codepoints、grapheme_clusters 及索引。
# polyglot-family: text_binary_and_serialization
# polyglot-concept: unicode_strings_and_code_units
# polyglot-related: languages/ruby/language/07_strings_regex_and_patterns/test_049_bytes_codepoints_and_graphemes.rb

require "assertions"

A = PolyglotAssertions

text = "A\u{1F600}e\u0301\u0000"
A.equal(9, text.bytesize)
A.equal(5, text.length)
A.equal([65, 0x1F600, 101, 769, 0], text.codepoints)
A.equal(["A", "\u{1F600}", "e\u0301", "\u0000"], text.grapheme_clusters)
A.equal("\u{1F600}", text[1])
A.equal(0, text.getbyte(-1))
A.same(Encoding::UTF_8, text.encoding)

A.done
