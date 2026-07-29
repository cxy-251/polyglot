# polyglot-covers: julia.language.immutable-mutable-identity-and-aliasing

using Test

struct ImmutablePoint
    x::Int
    values::Vector{Int}
end

mutable struct MutablePoint
    x::Int
end

@testset "immutable 固定字段 binding，mutable 对象拥有可观察身份" begin
    immutable = ImmutablePoint(1, [2])
    @test_throws ErrorException setfield!(immutable, :x, 3)
    push!(immutable.values, 4)
    @test immutable.values == [2, 4]
    first = MutablePoint(1)
    second = MutablePoint(1)
    alias = first
    @test first !== second
    @test first === alias
    alias.x = 3
    @test first.x == 3
    @test second.x == 1
end
