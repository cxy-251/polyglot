# 共同问题：alignment、offset 和 owner lifetime 怎样约束二进制访问。
# 输入：显式 padding、非对齐 offset、String owner 和 Fiddle Pointer；观察：格式控制与所有权责任。
# polyglot-family: text_binary_and_serialization
# polyglot-concept: binary_buffers_views_and_endianness
# polyglot-related: languages/ruby/standard_library/12_gc_introspection_and_ffi/
# polyglot-related+: test_095_fiddle_dynamic_library_boundary.rb

require "assertions"
require "fiddle"

A = PolyglotAssertions

packed = [0xAA, 0x1234].pack("Cx n")
A.equal([0xAA, 0, 0x12, 0x34], packed.bytes)
A.equal(0x1234, packed.unpack1("n", offset: 2))

unaligned = "\x00\x78\x56\x34\x12".b
A.equal(0x12345678, unaligned.unpack1("L<", offset: 1))

owner = +"ruby\0"
pointer = Fiddle::Pointer[owner]
A.equal("ruby", pointer.to_s)
A.equal(owner.bytesize, pointer.to_s(owner.bytesize).bytesize)

A.done
