# polyglot-covers: julia.language.array-shape-axes-and-bounds

using Test

@testset "数组维度、轴、线性顺序和边界是显式协议" begin
    matrix = reshape(collect(1:6), 2, 3)
    @test size(matrix) == (2, 3)
    @test axes(matrix) == (Base.OneTo(2), Base.OneTo(3))
    @test matrix[2, 3] == 6
    @test vec(matrix) == collect(1:6)
    @test ndims(matrix) == 2
    @test firstindex(matrix) == 1
    @test lastindex(matrix) == 6
    @test matrix[CartesianIndex(2, 2)] == 4
    @test checkbounds(Bool, matrix, 2, 3)
    @test !checkbounds(Bool, matrix, 3, 1)
    @test_throws BoundsError matrix[0]
end
