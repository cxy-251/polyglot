# polyglot-covers: julia.language.array-shape-axes-and-column-major-order

using Test

@testset "数组维度、轴和线性顺序是显式可查询的" begin
    matrix = reshape(collect(1:6), 2, 3)
    @test size(matrix) == (2, 3)
    @test axes(matrix) == (Base.OneTo(2), Base.OneTo(3))
    @test matrix[2, 3] == 6
    @test vec(matrix) == collect(1:6)
    @test ndims(matrix) == 2
end
