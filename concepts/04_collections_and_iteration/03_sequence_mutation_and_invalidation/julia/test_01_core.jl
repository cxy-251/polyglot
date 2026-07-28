# polyglot-family: collections_and_iteration
# polyglot-concept: sequence_mutation_and_invalidation
# polyglot-related: languages/julia/language/06_arrays_indexing_iteration_and_broadcast/
# polyglot-related+: test_044_array_mutation_capacity_and_alias_boundaries.jl
#
# 共同问题：原地修改怎样被别名观察；结构修改后的索引是否仍指向同一元素。
# 对照观察：带 ! API 修改同一 Vector；插入删除改变后续位置，旧整数索引不携带元素身份。

using Test

@testset "结构修改保留对象身份但改变位置" begin
    values = [10, 20, 30]
    alias = values
    insert!(values, 2, 15)
    @test alias === values
    @test alias == [10, 15, 20, 30]
    deleteat!(values, 1)
    @test values[2] == 20
    @test push!(values, 40) === values
end
