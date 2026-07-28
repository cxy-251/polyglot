# polyglot-family: collections_and_iteration
# polyglot-concept: sorting_stability_and_custom_order
# polyglot-related: languages/julia/language/06_arrays_indexing_iteration_and_broadcast/
# polyglot-related+: test_048_mapping_reduction_and_stable_sorting.jl
#
# 共同问题：相等排序键的输入顺序是否保留；怎样按派生键和反向顺序排序。
# 对照观察：Julia 可显式选择稳定 MergeSort；by 只提取键，rev 反转同一 ordering。

using Test

@testset "稳定算法保留相等 key 的相对顺序" begin
    rows = [(key = 2, name = :a), (key = 1, name = :b), (key = 2, name = :c)]
    ordered = sort(rows; by = row -> row.key, alg = MergeSort)
    @test getproperty.(ordered, :name) == [:b, :a, :c]
    @test sort([1, 3, 2]; rev = true) == [3, 2, 1]
    @test sortperm([20, 10, 20]; alg = MergeSort) == [2, 1, 3]
end
