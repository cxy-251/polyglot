# frozen_string_literal: true
# polyglot-covers: ruby.text.encoding-transcoding-and-invalid-bytes

require "assertions"

A = PolyglotAssertions

utf8 = "café"
latin1 = utf8.encode(Encoding::ISO_8859_1)
A.same(Encoding::ISO_8859_1, latin1.encoding)
A.equal(4, latin1.bytesize)
A.equal(utf8, latin1.encode(Encoding::UTF_8))

invalid = "\xFF".b.force_encoding(Encoding::UTF_8)
A.falsey(invalid.valid_encoding?)
A.raises(Encoding::InvalidByteSequenceError) { invalid.encode(Encoding::UTF_16LE) }
replaced = invalid.scrub("?")
A.equal("?", replaced)
A.truth(replaced.valid_encoding?)

A.done
