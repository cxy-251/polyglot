# polyglot-covers: julia.language.multiple-dispatch-across-arguments

using Test

combine(left::Int, right::Int) = left + right
combine(left::AbstractString, right::AbstractString) = left * right
combine(left, right) = (left, right)

@testset "multiple dispatch 使用全部位置参数类型选择方法" begin
    @test combine(2, 3) == 5
    @test combine("a", "b") == "ab"
    @test combine(1, "b") == (1, "b")
    @test length(methods(combine)) == 3
end
