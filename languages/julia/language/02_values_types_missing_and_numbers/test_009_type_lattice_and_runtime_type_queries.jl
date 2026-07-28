# polyglot-covers: julia.language.type-lattice-and-runtime-queries

using Test

@testset "类型格、实例关系与子类型关系是不同查询" begin
    @test typeof(1) === Int
    @test 1 isa Integer
    @test Int <: Signed <: Integer <: Real <: Number
    @test !(Float64 <: Integer)
    @test supertype(Int) === Signed
end
