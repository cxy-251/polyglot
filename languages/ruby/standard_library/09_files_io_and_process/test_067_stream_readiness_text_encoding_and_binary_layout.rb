# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.io-pipes-binary-and-text-encoding

require "assertions"

A = PolyglotAssertions

A.case("IO.select reports pipe readiness and text reads retain the configured encoding") do
  reader, writer = IO.pipe(Encoding::UTF_8, Encoding::UTF_8)
  begin
    writer.write("café\n")
    writer.close
    ready_readers, ready_writers = IO.select([reader], [], [], 0)
    A.equal([reader], ready_readers)
    A.equal([], ready_writers)

    line = reader.gets
    A.equal("café\n", line)
    A.same(Encoding::UTF_8, line.encoding)
    A.truth(reader.eof?)
  ensure
    reader.close unless reader.closed?
    writer.close unless writer.closed?
  end
end

A.case("binary Strings expose bytes while pack directives define field endianness") do
  binary = String.new("\x00\xFF", encoding: Encoding::BINARY)
  A.equal([0, 255], binary.bytes)
  A.same(Encoding::ASCII_8BIT, binary.encoding)
  A.equal("\x12\x34\x78\x56".b, [0x1234, 0x5678].pack("nS<"))
  A.equal([0x1234, 0x5678], "\x12\x34\x78\x56".b.unpack("nS<"))
end

A.done
