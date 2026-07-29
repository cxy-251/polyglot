# 共同问题：规范等价文本和非法字节怎样处理。
# 输入：NFC/NFD、UTF-8 非法字节、valid_encoding?、scrub 和 transcoding；观察：显式规范化及错误策略。
# polyglot-family: text_binary_and_serialization
# polyglot-concept: unicode_strings_and_code_units
# polyglot-related: languages/ruby/language/07_strings_regex_and_patterns/
# polyglot-related+: test_050_encoding_transcoding_and_invalid_bytes.rb

require "assertions"

A = PolyglotAssertions

composed = "\u00E9"
decomposed = "e\u0301"
A.falsey(composed == decomposed)
A.equal(composed, decomposed.unicode_normalize(:nfc))
A.equal(decomposed, composed.unicode_normalize(:nfd))

invalid = "\xFF".b.force_encoding(Encoding::UTF_8)
A.falsey(invalid.valid_encoding?)
A.equal("?", invalid.scrub("?"))
A.raises(Encoding::InvalidByteSequenceError) { invalid.encode(Encoding::UTF_16LE) }

A.done
