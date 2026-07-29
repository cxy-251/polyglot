# polyglot-covers: julia.language.type-lattice-nothing-and-unions

using Test

find_even(values) = findfirst(iseven, values)

@testset "类型格、实例查询和可选 Union 属于同一值模型" begin
    @test typeof(1) === Int
    @test 1 isa Integer
    @test Int <: Signed <: Integer <: Real <: Number
    @test !(Float64 <: Integer)
    @test supertype(Int) === Signed
    @test nothing isa Nothing
    @test find_even([1, 3]) === nothing
    @test find_even([1, 4]) == 2
    @test Union{Nothing,Int} === Union{Int,Nothing}
    @test something(nothing, 7) == 7
    @test_throws ArgumentError something(nothing)
end
