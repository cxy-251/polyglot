# polyglot-covers: julia.language.nothing-and-optional-unions

using Test

find_even(values) = findfirst(iseven, values)

@testset "nothing 表示一个值缺席且类型为 Nothing" begin
    @test nothing isa Nothing
    @test find_even([1, 3]) === nothing
    @test find_even([1, 4]) == 2
    @test Union{Nothing,Int} === Union{Int,Nothing}
    @test something(nothing, 7) == 7
end
