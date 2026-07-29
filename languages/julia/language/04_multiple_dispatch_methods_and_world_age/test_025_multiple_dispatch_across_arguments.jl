# polyglot-covers: julia.language.multiple-dispatch-specificity-and-constraints

using Test

combine(left::Int, right::Int) = left + right
combine(left::AbstractString, right::AbstractString) = left * right
combine(left, right) = (left, right)

category(value::Number) = :number
category(value::Integer) = :integer
category(value::Int) = :machine_integer
category(value) = :other

same_type(left::T, right::T) where {T} = T
same_type(left, right) = nothing

describe(value::Number) = "number:$value"
describe(value::Int) = "int:$value"

@testset "multiple dispatch 按全部位置参数和 specificity 选择方法" begin
    @test combine(2, 3) == 5
    @test combine("a", "b") == "ab"
    @test combine(1, "b") == (1, "b")
    @test length(methods(combine)) == 3
    @test category(1) === :machine_integer
    @test category(big"1") === :integer
    @test category(1.5) === :number
    @test category("1") === :other
    @test same_type(1, 2) === Int
    @test same_type(1, 2.0) === nothing
    @test describe(3) == "int:3"
    @test invoke(describe, Tuple{Number}, 3) == "number:3"
end
