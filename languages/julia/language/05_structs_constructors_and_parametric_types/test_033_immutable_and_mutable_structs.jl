# polyglot-covers: julia.language.immutable-and-mutable-structs

using Test

struct ImmutablePoint
    x::Int
    values::Vector{Int}
end

mutable struct MutablePoint
    x::Int
end

@testset "immutable 固定字段 binding，mutable 允许字段重绑定" begin
    immutable = ImmutablePoint(1, [2])
    @test_throws ErrorException setfield!(immutable, :x, 3)
    push!(immutable.values, 4)
    @test immutable.values == [2, 4]
    mutable = MutablePoint(1)
    mutable.x = 3
    @test mutable.x == 3
end
