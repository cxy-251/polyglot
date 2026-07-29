# polyglot-family: text_binary_and_serialization
# polyglot-concept: binary_buffers_views_and_endianness
# polyglot-related: languages/julia/tooling_and_runtime/16_ffi_pointers_and_unsafe_boundaries/
# polyglot-related+: test_123_cconvert_unsafe_convert_and_gc_preserve.jl
#
# 共同问题：typed view 对大小和对齐有什么要求；裸 pointer 的有效期由谁保证。
# 对照观察：reinterpret 要求字节尺寸可整除；unsafe pointer 操作由调用方用拥有对象和 GC.@preserve 约束。

using Test

@testset "typed bytes 和 pointer 需要显式前置条件" begin
    @test_throws ArgumentError reinterpret(UInt32, UInt8[1, 2, 3])
    storage = Ref{UInt32}(0x01020304)
    pointer = Base.unsafe_convert(Ptr{UInt32}, storage)
    GC.@preserve storage begin
        @test unsafe_load(pointer) == 0x01020304
        unsafe_store!(pointer, 0x05060708)
        @test storage[] == 0x05060708
    end
end
