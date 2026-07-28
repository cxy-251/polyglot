# polyglot-covers: julia.stdlib.serialization-roundtrip-and-trust-boundary

using Test
using Serialization

@testset "Serialization 保留 Julia 对象图但不是不可信输入格式" begin
    shared = [1, 2]
    value = (left = shared, right = shared)
    buffer = IOBuffer()
    serialize(buffer, value)
    seekstart(buffer)
    decoded = deserialize(buffer)
    @test decoded == value
    @test decoded.left === decoded.right
    @test position(buffer) > 0
    # 格式可能随 Julia 版本变化，且 deserialize 不应用于不可信字节。
    @test decoded.left !== shared
end
