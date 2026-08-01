# frozen_string_literal: true
# polyglot-covers: ruby.text.encoding-transcoding-and-invalid-bytes

require "assertions"

A = PolyglotAssertions

A.case("encode transcodes bytes and records the destination encoding") do
  utf8 = "café"
  latin1 = utf8.encode(Encoding::ISO_8859_1)
  A.same(Encoding::ISO_8859_1, latin1.encoding)
  A.equal(4, latin1.bytesize)
  A.equal(utf8, latin1.encode(Encoding::UTF_8))
end

A.case("invalid byte sequences may raise during transcoding or be explicitly scrubbed") do
  invalid = "\xFF".b.force_encoding(Encoding::UTF_8)
  A.falsey(invalid.valid_encoding?)
  A.raises(Encoding::InvalidByteSequenceError) { invalid.encode(Encoding::UTF_16LE) }
  replaced = invalid.scrub("?")
  A.equal("?", replaced)
  A.truth(replaced.valid_encoding?)
end

A.case("the process-wide default internal encoding is restored after scoped use") do
  original_internal = Encoding.default_internal
  begin
    Encoding.default_internal = Encoding::UTF_8
    A.same(Encoding::UTF_8, Encoding.default_internal)
    A.same(Encoding::UTF_8, "ruby".encode.encoding)
  ensure
    Encoding.default_internal = original_internal
  end
  A.same(original_internal, Encoding.default_internal)
end

A.done
