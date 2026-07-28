# polyglot-covers: julia.language.union-types-typejoin-and-narrowing

using Test

function optional_length(value::Union{Nothing,AbstractString})
    value === nothing && return 0
    return length(value)
end

@testset "Union 表达有限候选，typejoin 计算共同抽象上界" begin
    @test optional_length(nothing) == 0
    @test optional_length("abc") == 3
    @test typejoin(Int, Float64) === Real
    @test Union{} <: Int
    @test Union{Int,String} <: Any
end
