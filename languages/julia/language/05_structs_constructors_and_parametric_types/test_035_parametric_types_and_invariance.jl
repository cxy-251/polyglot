# polyglot-covers: julia.language.parametric-types-hierarchy-unions-and-invariance

using Test

struct PairBox{T}
    first::T
    second::T
end

abstract type CourseNumber <: Number end
primitive type Token64 <: CourseNumber 64 end

optional_length(value::Union{Nothing,AbstractString}) =
    value === nothing ? 0 : length(value)

@testset "参数化类型保持不变性，abstract/Union 描述允许的上界" begin
    box = PairBox(1, 2)
    @test typeof(box) === PairBox{Int}
    @test PairBox{Int} <: PairBox
    @test !(PairBox{Int} <: PairBox{Real})
    @test PairBox{Int} !== PairBox{Int32}
    @test !isconcretetype(CourseNumber)
    @test isconcretetype(Token64)
    @test sizeof(Token64) == 8
    @test Token64 <: CourseNumber <: Number
    @test optional_length(nothing) == 0
    @test optional_length("abc") == 3
    @test typejoin(Int, Float64) === Real
    @test Union{} <: Int
end
