# polyglot-covers: julia.language.parametric-types-and-invariance

using Test

struct PairBox{T}
    first::T
    second::T
end

@testset "参数化 concrete type 不随参数协变" begin
    box = PairBox(1, 2)
    @test typeof(box) === PairBox{Int}
    @test PairBox{Int} <: PairBox
    @test !(PairBox{Int} <: PairBox{Real})
    @test PairBox{Int} !== PairBox{Int32}
end
