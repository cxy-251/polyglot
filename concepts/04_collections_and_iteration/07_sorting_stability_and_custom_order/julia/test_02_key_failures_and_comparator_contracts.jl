# polyglot-family: collections_and_iteration
# polyglot-concept: sorting_stability_and_custom_order
# polyglot-related: languages/julia/language/06_arrays_indexing_iteration_and_broadcast/
# polyglot-related+: test_048_mapping_reduction_and_stable_sorting.jl
#
# 共同问题：key 提取失败怎样传播；自定义 comparator 必须满足什么契约。
# 对照观察：by/lt 的异常直接传播；lt 应定义 strict weak order，反向数值顺序可用 isless 参数交换。

using Test

@testset "排序不吞掉 key 错误" begin
    @test_throws FieldError sort([1, 2]; by = value -> getproperty(value, :missing))
    descending = sort([1, 3, 2]; lt = (left, right) -> isless(right, left))
    @test descending == [3, 2, 1]
    @test sort(["bbb", "a", "cc"]; by = length) == ["a", "cc", "bbb"]
end
