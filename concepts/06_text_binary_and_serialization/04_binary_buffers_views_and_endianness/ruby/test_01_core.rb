# 共同问题：二进制缓冲区怎样表达字节、切片和端序。
# 输入：ASCII-8BIT String、pack/unpack、大端、小端及 byteslice；观察：可变字节存储和复制边界。
# polyglot-family: text_binary_and_serialization
# polyglot-concept: binary_buffers_views_and_endianness
# polyglot-related: languages/ruby/standard_library/09_files_io_and_process/
# polyglot-related+: test_067_stream_readiness_text_encoding_and_binary_layout.rb

require "assertions"

A = PolyglotAssertions

big_endian = [0x1234, 0x5678].pack("n2")
little_endian = [0x1234, 0x5678].pack("v2")
A.same(Encoding::ASCII_8BIT, big_endian.encoding)
A.equal([0x12, 0x34, 0x56, 0x78], big_endian.bytes)
A.equal([0x34, 0x12, 0x78, 0x56], little_endian.bytes)
A.equal([0x1234, 0x5678], big_endian.unpack("n2"))

slice = big_endian.byteslice(0, 2)
slice.setbyte(0, 0)
A.equal(0x12, big_endian.getbyte(0))
A.equal(0, slice.getbyte(0))

A.done
