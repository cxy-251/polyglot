# polyglot-family: values_and_comparison
# polyglot-concept: equality
# polyglot-related: languages/julia/language/02_values_types_missing_and_numbers/
# polyglot-related+: test_012_equality_identity_and_nan.jl
#
# 共同问题：值相等、键相等与对象身份如何区分；NaN 和缺失值如何比较。
# 对照观察：== 可传播 missing，isequal 给容器键稳定布尔结果，=== 比较同一对象或不可变值。

using Test

@testset "三种相等关系回答不同问题" begin
    @test isequal(missing, missing)
    @test ismissing(missing == missing)
    @test NaN != NaN
    @test isequal(NaN, NaN)
    left = [1]
    @test left == [1]
    @test left !== [1]
end
