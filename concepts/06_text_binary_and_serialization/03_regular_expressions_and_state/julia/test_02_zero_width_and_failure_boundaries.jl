# polyglot-family: text_binary_and_serialization
# polyglot-concept: regular_expressions_and_state
# polyglot-related: languages/julia/language/07_unicode_exceptions_and_resources/
# polyglot-related+: test_053_regular_expressions_and_match_state.jl
#
# 共同问题：零宽匹配如何推进；模式编译失败和无匹配是否使用同一通道。
# 对照观察：零宽结果仍是成功 RegexMatch；无匹配返回 nothing，非法模式在 Regex 构造时抛异常。

using Test

@testset "零宽、无匹配与非法模式是三种结果" begin
    zero_width = match(r"^", "")
    @test zero_width !== nothing
    @test zero_width.match == ""
    @test zero_width.offset == 1
    @test match(r"x", "") === nothing
    @test_throws ErrorException Regex("(")
end
