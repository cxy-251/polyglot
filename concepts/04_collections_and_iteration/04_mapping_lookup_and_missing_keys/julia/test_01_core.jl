# polyglot-family: collections_and_iteration
# polyglot-concept: mapping_lookup_and_missing_keys
# polyglot-related: languages/julia/standard_library/08_collections_ranges_and_copying/
# polyglot-related+: test_058_dict_lookup_insertion_and_merge.jl
#
# 共同问题：缺失键怎样区分异常、默认值和插入；查询是否意外修改映射。
# 对照观察：索引抛 KeyError，get 只返回默认值，get! 在缺失时插入，haskey 不读取值。

using Test

@testset "lookup API 明确区分只读与写入" begin
    mapping = Dict(:ready => 1)
    @test mapping[:ready] == 1
    @test_throws KeyError mapping[:missing]
    @test get(mapping, :missing, 0) == 0
    @test !haskey(mapping, :missing)
    @test get!(mapping, :missing, 2) == 2
    @test mapping[:missing] == 2
end
