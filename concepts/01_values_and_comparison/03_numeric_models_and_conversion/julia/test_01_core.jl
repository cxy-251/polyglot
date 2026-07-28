# polyglot-family: values_and_comparison
# polyglot-concept: numeric_models_and_conversion
# polyglot-related: languages/julia/language/02_values_types_missing_and_numbers/
# polyglot-related+: test_016_promotion_rules_and_common_types.jl
#
# 共同问题：整数除法、溢出、显式转换和混合类型算术采用什么模型。
# 对照观察：Julia 固定宽度整数按类型运算，convert 拒绝不精确整数，promotion 选择共同表示。

using Test

@testset "转换与 promotion 明确分层" begin
    @test 7 ÷ 2 == 3
    @test 7 / 2 == 3.5
    @test_throws InexactError convert(Int, 1.5)
    @test promote(1, 2.5) == (1.0, 2.5)
    @test typeof(Int8(1) + Int8(2)) === Int8
    @test typemax(Int8) + Int8(1) == typemin(Int8)
end
