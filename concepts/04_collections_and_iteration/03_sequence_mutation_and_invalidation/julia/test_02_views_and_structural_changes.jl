# polyglot-family: collections_and_iteration
# polyglot-concept: sequence_mutation_and_invalidation
# polyglot-related: languages/julia/language/06_arrays_indexing_iteration_and_broadcast/
# polyglot-related+: test_043_slice_copies_and_view_aliases.jl
#
# 共同问题：view 是否共享存储；父容器结构改变后 view 的范围是否自动扩展。
# 对照观察：SubArray 保存父数组与索引选择，元素修改双向可见；固定范围不会因 parent push! 自动增长。

using Test

@testset "view 共享元素但保持自己的 axes" begin
    parent = [1, 2, 3]
    window = @view parent[2:3]
    window[1] = 20
    @test parent == [1, 20, 3]
    push!(parent, 4)
    @test length(window) == 2
    @test collect(window) == [20, 3]
    @test parent == [1, 20, 3, 4]
end
