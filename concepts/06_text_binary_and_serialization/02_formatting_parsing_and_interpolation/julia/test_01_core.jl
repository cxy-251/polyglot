# polyglot-family: text_binary_and_serialization
# polyglot-concept: formatting_parsing_and_interpolation
# polyglot-related: languages/julia/language/07_unicode_exceptions_and_resources/
# polyglot-related+: test_051_interpolation_show_and_printf_formatting.jl
#
# 共同问题：插值、格式化和解析怎样选择表示；解析失败采用值还是异常。
# 对照观察：$ 插值调用字符串展示，Printf 固定格式；parse 抛异常而 tryparse 返回 nothing。

using Test
using Printf

@testset "文本输入输出协议显式分层" begin
    value = 3.5
    @test "value=$(value)" == "value=3.5"
    @test @sprintf("%.2f", value) == "3.50"
    @test parse(Int, "42") == 42
    @test tryparse(Int, "forty-two") === nothing
    @test_throws ArgumentError parse(Int, "forty-two")
end
