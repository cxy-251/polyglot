# polyglot-family: text_binary_and_serialization
# polyglot-concept: serialization_clone_and_transfer
# polyglot-related: languages/julia/standard_library/09_text_data_dates_and_math/
# polyglot-related+: test_068_serialization_roundtrip_and_trust_boundary.jl
#
# 共同问题：序列化是否保留对象图和别名；roundtrip 是否等同于通用交换格式。
# 对照观察：Serialization 面向 Julia 对象图并保留内部共享，不承诺跨版本通用数据交换。

using Test
using Serialization

@testset "roundtrip 保留图内共享关系" begin
    shared = [1, 2]
    graph = (shared, shared)
    buffer = IOBuffer()
    serialize(buffer, graph)
    seekstart(buffer)
    restored = deserialize(buffer)
    @test restored == graph
    @test restored[1] === restored[2]
    @test restored[1] !== shared
end
