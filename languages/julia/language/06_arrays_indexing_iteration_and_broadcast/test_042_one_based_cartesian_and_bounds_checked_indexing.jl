# polyglot-covers: julia.language.one-based-cartesian-and-bounds-indexing

using Test

@testset "默认数组一基索引并支持 CartesianIndex" begin
    matrix = [1 2; 3 4]
    @test firstindex(matrix) == 1
    @test lastindex(matrix) == 4
    @test matrix[CartesianIndex(2, 1)] == 3
    @test checkbounds(Bool, matrix, 2, 2)
    @test !checkbounds(Bool, matrix, 3, 1)
    @test_throws BoundsError matrix[0]
end
