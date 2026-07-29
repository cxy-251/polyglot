# polyglot-family: collections_and_iteration
# polyglot-concept: indexing_slicing_and_bounds
# polyglot-related: languages/julia/language/06_arrays_indexing_iteration_and_broadcast/
# polyglot-related+: test_041_array_shape_axes_and_column_major_order.jl
#
# 共同问题：索引起点、slice 端点和越界行为是什么；多维索引怎样表达。
# 对照观察：Julia 数组默认一基且区间两端闭合；普通 slice 复制，越界在 bounds checking 下抛 BoundsError。

using Test

@testset "索引、slice 与 bounds 是显式协议" begin
    matrix = [1 2; 3 4]
    @test firstindex(matrix, 1) == 1
    @test matrix[2, 1] == 3
    @test matrix[1:2, 1] == [1, 3]
    @test_throws BoundsError matrix[0, 1]
    slice = matrix[:, 1]
    slice[1] = 99
    @test matrix[1, 1] == 1
end
