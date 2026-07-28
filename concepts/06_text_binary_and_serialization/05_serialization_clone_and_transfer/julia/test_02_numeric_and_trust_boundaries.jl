# polyglot-family: text_binary_and_serialization
# polyglot-concept: serialization_clone_and_transfer
# polyglot-related: languages/julia/standard_library/09_text_data_dates_and_math/
# polyglot-related+: test_068_serialization_roundtrip_and_trust_boundary.jl
#
# 共同问题：数值表示和类型身份能否无损往返；损坏或不可信输入如何处理。
# 对照观察：Serialization 保留 Julia 数值类型，但格式可执行任意对象重建逻辑，只用于可信且兼容的数据。

using Test
using Serialization

@testset "类型保真不等于安全交换格式" begin
    buffer = IOBuffer()
    serialize(buffer, (Int8(1), big"12345678901234567890"))
    seekstart(buffer)
    restored = deserialize(buffer)
    @test restored[1] isa Int8
    @test restored[2] isa BigInt
    @test_throws EOFError deserialize(IOBuffer(UInt8[]))
end
