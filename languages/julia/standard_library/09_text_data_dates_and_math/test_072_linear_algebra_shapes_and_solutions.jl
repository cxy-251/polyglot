# polyglot-covers: julia.stdlib.linear-algebra-shapes-and-solutions

using Test
using LinearAlgebra

@testset "LinearAlgebra 使用形状和元素类型定义运算" begin
    matrix = [3.0 1.0; 1.0 2.0]
    right = [9.0, 8.0]
    solution = matrix \ right
    @test solution ≈ [2.0, 3.0]
    @test dot([1, 2], [3, 4]) == 11
    @test tr(matrix) == 5.0
    @test Matrix(I, 2, 2) == [1 0; 0 1]
end
