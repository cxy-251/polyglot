# polyglot-family: collections_and_iteration
# polyglot-concept: sets_membership_and_deduplication
# polyglot-related: languages/julia/standard_library/08_collections_ranges_and_copying/
# polyglot-related+: test_059_set_membership_and_algebra.jl
#
# 共同问题：集合用哪种相等关系去重；成员关系和集合代数是否保留输入顺序。
# 对照观察：Set 使用 isequal/hash，面向成员而非顺序；NaN 可稳定去重，signed zero 保持不同键。

using Test

@testset "Set 的成员语义复用键协议" begin
    values = Set([NaN, NaN, -0.0, 0.0])
    @test length(values) == 3
    @test NaN in values
    @test -0.0 in values
    @test 0.0 in values
    @test Set([1, 2]) ∩ Set([2, 3]) == Set([2])
end
